from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.system_check import _load_strategy_services


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def _strategy_service_modules() -> tuple[Any, Any, Any]:
    import sys

    from app.services.system_check import PROJECT_ROOT

    strategy_dir = PROJECT_ROOT / "strategies"
    if str(strategy_dir) not in sys.path:
        sys.path.insert(0, str(strategy_dir))

    from services import generation_service, runtime_service, spec_service

    return generation_service, runtime_service, spec_service


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


def materialize_strategy(strategy_slug: str, profile_name: str | None = None) -> dict[str, Any]:
    db_service = _db_service()
    generation_service, runtime_service, spec_service = _strategy_service_modules()

    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    effective_spec = spec_service.apply_profile_overrides(spec, profile)
    code = generation_service.generate_strategy(strategy_slug, effective_spec)
    runtime_service.RUNTIME_STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
    runtime_service.RUNTIME_PARAM_DIR.mkdir(parents=True, exist_ok=True)

    strategy_path = runtime_service.RUNTIME_STRATEGY_DIR / f"auto_{strategy_slug}.py"
    params_path = runtime_service.RUNTIME_STRATEGY_DIR / f"auto_{strategy_slug}.json"
    params = runtime_service.build_freqtrade_params(
        strategy_slug,
        effective_spec,
        profile.get("profile_name"),
    )
    params_text = json.dumps(params, ensure_ascii=False, indent=2)

    strategy_path.write_text(code, encoding="utf-8")
    params_path.write_text(params_text, encoding="utf-8")

    strategy_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    params_hash = hashlib.sha256(params_text.encode("utf-8")).hexdigest()
    db_service.record_runtime_artifact(
        strategy_slug=strategy_slug,
        profile_name=profile["profile_name"],
        artifact_type="freqtrade_strategy_py",
        artifact_path=strategy_path,
        content=code,
        metadata={"class_name": runtime_service.strategy_class_name(strategy_slug)},
    )
    db_service.record_runtime_artifact(
        strategy_slug=strategy_slug,
        profile_name=profile["profile_name"],
        artifact_type="freqtrade_params_json",
        artifact_path=params_path,
        content=params_text,
        metadata={"strategy_name": runtime_service.strategy_class_name(strategy_slug)},
    )

    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile["profile_name"],
        "artifacts": [
            {
                "artifact_type": "freqtrade_strategy_py",
                "artifact_path": str(strategy_path),
                "artifact_hash": strategy_hash,
            },
            {
                "artifact_type": "freqtrade_params_json",
                "artifact_path": str(params_path),
                "artifact_hash": params_hash,
            },
        ],
    }
