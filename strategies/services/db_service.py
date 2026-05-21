import hashlib
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from psycopg2.extras import Json, RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


SCHEMA_SQL = """
create table if not exists strategy_specs (
  id bigserial primary key,
  slug text not null unique,
  name text not null,
  description text,
  status text not null default 'draft',
  spec jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists strategy_profiles (
  id bigserial primary key,
  strategy_slug text not null references strategy_specs(slug) on delete cascade,
  profile_name text not null,
  status text not null default 'draft',
  source text,
  is_active boolean not null default false,
  overrides jsonb not null default '{}'::jsonb,
  validation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(strategy_slug, profile_name)
);

create unique index if not exists strategy_profiles_one_active
  on strategy_profiles(strategy_slug)
  where is_active;

create table if not exists strategy_promotion_events (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  from_status text,
  to_status text not null,
  reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists strategy_validation_results (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  timerange text not null,
  passed boolean not null,
  metrics jsonb not null,
  gate jsonb not null,
  warnings jsonb not null default '[]'::jsonb,
  failed_checks jsonb not null default '[]'::jsonb,
  artifact_path text,
  created_at timestamptz not null default now()
);

create table if not exists strategy_runtime_artifacts (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  artifact_type text not null,
  artifact_path text not null,
  artifact_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
"""


def load_env_file() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def database_url() -> str:
    load_env_file()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return to_psycopg_url(url)


def to_psycopg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    return url


def database_name(url: str | None = None) -> str:
    parts = urlsplit(to_psycopg_url(url or database_url()))
    return parts.path.lstrip("/")


def admin_database_url(url: str | None = None) -> str:
    parts = urlsplit(to_psycopg_url(url or database_url()))
    return urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))


def connect(url: str | None = None):
    return psycopg2.connect(url or database_url(), cursor_factory=RealDictCursor)


def ensure_database() -> str:
    target_url = database_url()
    target_db = database_name(target_url)
    admin_url = admin_database_url(target_url)
    with psycopg2.connect(admin_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("select 1 from pg_database where datname = %s", (target_db,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'create database "{target_db}"')
    return target_db


def init_schema() -> None:
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)


def upsert_spec(slug: str, spec: dict) -> None:
    init_schema()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into strategy_specs(slug, name, description, status, spec)
                values (%s, %s, %s, %s, %s)
                on conflict (slug) do update set
                  name = excluded.name,
                  description = excluded.description,
                  spec = excluded.spec,
                  updated_at = now()
                """,
                (
                    slug,
                    spec.get("name", slug),
                    spec.get("description"),
                    spec.get("status", "draft"),
                    Json(spec),
                ),
            )


def upsert_profile(strategy_slug: str, profile: dict, *, is_active: bool = False) -> None:
    init_schema()
    profile_name = profile.get("profile_name")
    if not profile_name:
        raise RuntimeError(f"profile_name is required for {strategy_slug}")
    with connect() as conn:
        with conn.cursor() as cur:
            if is_active:
                cur.execute("update strategy_profiles set is_active = false where strategy_slug = %s", (strategy_slug,))
            cur.execute(
                """
                insert into strategy_profiles(
                  strategy_slug, profile_name, status, source, is_active, overrides, validation
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (strategy_slug, profile_name) do update set
                  status = excluded.status,
                  source = excluded.source,
                  is_active = excluded.is_active,
                  overrides = excluded.overrides,
                  validation = excluded.validation,
                  updated_at = now()
                """,
                (
                    strategy_slug,
                    profile_name,
                    profile.get("status", "draft"),
                    profile.get("source"),
                    is_active,
                    Json(profile.get("overrides", {})),
                    Json(profile.get("validation", {})),
                ),
            )


def list_registry() -> list[dict]:
    init_schema()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  s.slug,
                  s.name,
                  s.status,
                  count(p.id)::int as profile_count,
                  max(p.profile_name) filter (where p.is_active) as active_profile
                from strategy_specs s
                left join strategy_profiles p on p.strategy_slug = s.slug
                group by s.slug, s.name, s.status
                order by s.slug
                """
            )
            return list(cur.fetchall())


def load_strategy_bundle(strategy_slug: str, profile_name: str | None = None) -> tuple[dict, dict]:
    init_schema()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select spec from strategy_specs where slug = %s", (strategy_slug,))
            spec_row = cur.fetchone()
            if not spec_row:
                raise RuntimeError(f"strategy not found in registry: {strategy_slug}")

            if profile_name:
                cur.execute(
                    """
                    select profile_name, status, source, overrides, validation
                    from strategy_profiles
                    where strategy_slug = %s and profile_name = %s
                    """,
                    (strategy_slug, profile_name),
                )
            else:
                cur.execute(
                    """
                    select profile_name, status, source, overrides, validation
                    from strategy_profiles
                    where strategy_slug = %s
                    order by is_active desc,
                      case status
                        when 'live_active' then 1
                        when 'paper_active' then 2
                        when 'validated' then 3
                        when 'candidate' then 4
                        else 5
                      end,
                      profile_name
                    limit 1
                    """,
                    (strategy_slug,),
                )
            profile_row = cur.fetchone()
            if not profile_row:
                raise RuntimeError(f"profile not found in registry: {strategy_slug}/{profile_name or '<active>'}")

    profile = dict(profile_row)
    profile["strategy_name"] = strategy_slug
    profile.setdefault("overrides", {})
    return dict(spec_row["spec"]), profile


def record_runtime_artifact(
    *,
    strategy_slug: str,
    profile_name: str,
    artifact_type: str,
    artifact_path: Path,
    content: str,
    metadata: dict | None = None,
) -> None:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    init_schema()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into strategy_runtime_artifacts(
                  strategy_slug, profile_name, artifact_type, artifact_path, artifact_hash, metadata
                )
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    strategy_slug,
                    profile_name,
                    artifact_type,
                    str(artifact_path),
                    digest,
                    Json(metadata or {}),
                ),
            )


def promote_profile(strategy_slug: str, profile_name: str, to_status: str, reason: str | None = None) -> None:
    init_schema()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select status from strategy_profiles where strategy_slug = %s and profile_name = %s",
                (strategy_slug, profile_name),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"profile not found in registry: {strategy_slug}/{profile_name}")
            from_status = row["status"]
            is_active = to_status in {"paper_active", "live_active"}
            if is_active:
                cur.execute("update strategy_profiles set is_active = false where strategy_slug = %s", (strategy_slug,))
            cur.execute(
                """
                update strategy_profiles
                set status = %s, is_active = %s, updated_at = now()
                where strategy_slug = %s and profile_name = %s
                """,
                (to_status, is_active, strategy_slug, profile_name),
            )
            cur.execute(
                """
                insert into strategy_promotion_events(strategy_slug, profile_name, from_status, to_status, reason)
                values (%s, %s, %s, %s, %s)
                """,
                (strategy_slug, profile_name, from_status, to_status, reason),
            )
