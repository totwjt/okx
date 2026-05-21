from __future__ import annotations

from typing import Any

from app.services.system_check import _load_strategy_services


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def list_strategies() -> list[dict[str, Any]]:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  s.slug,
                  s.name,
                  s.description,
                  s.status,
                  s.created_at,
                  s.updated_at,
                  count(p.id)::int as profile_count,
                  max(p.profile_name) filter (where p.is_active) as active_profile
                from strategy_specs s
                left join strategy_profiles p on p.strategy_slug = s.slug
                group by s.slug, s.name, s.description, s.status, s.created_at, s.updated_at
                order by s.slug
                """
            )
            return list(cur.fetchall())


def get_strategy(slug: str) -> dict[str, Any] | None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  s.slug,
                  s.name,
                  s.description,
                  s.status,
                  s.spec,
                  s.created_at,
                  s.updated_at,
                  count(p.id)::int as profile_count,
                  max(p.profile_name) filter (where p.is_active) as active_profile
                from strategy_specs s
                left join strategy_profiles p on p.strategy_slug = s.slug
                where s.slug = %s
                group by s.slug, s.name, s.description, s.status, s.spec, s.created_at, s.updated_at
                """,
                (slug,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def list_strategy_profiles(slug: str) -> list[dict[str, Any]] | None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from strategy_specs where slug = %s", (slug,))
            if not cur.fetchone():
                return None
            cur.execute(
                """
                select
                  profile_name,
                  status,
                  source,
                  is_active,
                  overrides,
                  validation,
                  created_at,
                  updated_at
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
                """,
                (slug,),
            )
            return list(cur.fetchall())


def list_runtime_artifacts(limit: int = 100) -> list[dict[str, Any]]:
    db_service = _db_service()
    db_service.init_schema()
    normalized_limit = max(1, min(limit, 500))
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  id,
                  strategy_slug,
                  profile_name,
                  artifact_type,
                  artifact_path,
                  artifact_hash,
                  metadata,
                  created_at
                from strategy_runtime_artifacts
                order by created_at desc, id desc
                limit %s
                """,
                (normalized_limit,),
            )
            return list(cur.fetchall())

