from __future__ import annotations

import ast
import hashlib
import json
import re
from typing import Any

from psycopg2.extras import Json

from app.services.system_check import _load_strategy_services

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
STRATEGY_DISPLAY_NAMES_ZH = {
    "grid_ls_v1": "网格多空 V1",
    "multi_ls_v2": "多空切换 V2",
    "multi_ls_v3": "多空结构化 V3",
    "scalping_v1": "短线剥头皮 V1",
}


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
            return [_decorate_strategy(row) for row in cur.fetchall()]


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
            return _decorate_strategy(row) if row else None


def _decorate_strategy(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    display_name = STRATEGY_DISPLAY_NAMES_ZH.get(str(item.get("slug")))
    if display_name:
        item["raw_name"] = item.get("name")
        item["name"] = display_name
    return item


def create_strategy_draft(
    *,
    slug: str,
    name: str,
    description: str,
    profile_name: str = "draft",
    thesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_slug = slug.strip()
    normalized_name = name.strip()
    normalized_description = description.strip()
    normalized_profile = profile_name.strip() or "draft"
    if not SLUG_RE.match(normalized_slug):
        raise RuntimeError("strategy slug must be 3-64 chars: lowercase letters, numbers, underscore, starting with a letter")
    if not normalized_name:
        raise RuntimeError("strategy Chinese name is required")
    if not normalized_description:
        raise RuntimeError("strategy description is required")

    spec = {
        "name": normalized_name,
        "description": normalized_description,
        "status": "draft",
        "lifecycle_origin": "web_hypothesis",
    }
    profile = {
        "profile_name": normalized_profile,
        "status": "draft",
        "source": "web_hypothesis",
        "overrides": {},
        "validation": {
            "thesis": thesis or {},
            "notes_zh": [
                "策略假设入口创建的草稿，只用于研究登记。",
                "补齐 spec 与参数边界后，才能生成运行产物或发起回测。",
            ],
        },
    }

    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from strategy_specs where slug = %s", (normalized_slug,))
            if cur.fetchone():
                raise RuntimeError(f"strategy already exists: {normalized_slug}")
            cur.execute(
                """
                insert into strategy_specs(slug, name, description, status, spec)
                values (%s, %s, %s, 'draft', %s)
                """,
                (normalized_slug, normalized_name, normalized_description, Json(spec)),
            )
            cur.execute(
                """
                insert into strategy_profiles(strategy_slug, profile_name, status, source, is_active, overrides, validation)
                values (%s, %s, 'draft', 'web_hypothesis', false, '{}'::jsonb, %s)
                """,
                (normalized_slug, normalized_profile, Json(profile["validation"])),
            )
    return {
        "strategy": get_strategy(normalized_slug),
        "profile": profile,
    }


def create_profile_draft(
    *,
    strategy_slug: str,
    profile_name: str,
    source_profile: str | None = None,
    overrides: dict[str, Any] | None = None,
    thesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db_service = _db_service()
    spec, baseline = db_service.load_strategy_bundle(strategy_slug, source_profile)
    normalized_profile = profile_name.strip()
    if not normalized_profile:
        raise RuntimeError("profile_name is required")
    profile = {
        "profile_name": normalized_profile,
        "status": "draft",
        "source": f"web_profile:{baseline['profile_name']}",
        "overrides": overrides or {},
        "validation": {
            "thesis": thesis or {},
            "baseline_profile": baseline["profile_name"],
            "strategy_name": spec.get("name", strategy_slug),
        },
    }
    db_service.upsert_profile(strategy_slug, profile, is_active=False)
    return {"strategy_slug": strategy_slug, "profile_name": normalized_profile, "profile": profile}


def update_strategy_definition(
    strategy_slug: str,
    spec: dict[str, Any],
    *,
    profile_name: str | None = None,
    profile_overrides: dict[str, Any] | None = None,
    profile_status: str = "candidate",
    source: str = "ai_generated_spec",
    validation: dict[str, Any] | None = None,
    activate_profile: bool = False,
) -> dict[str, Any]:
    if not isinstance(spec, dict) or not spec:
        raise RuntimeError("strategy spec is required")
    if not _has_executable_definition(spec):
        raise RuntimeError("strategy spec is incomplete; factors, entry/exit conditions, timeranges and risk_model are required")
    _validate_strategy_spec_executable(strategy_slug, spec)

    normalized_profile = (profile_name or "default").strip() or "default"
    name = str(spec.get("name") or strategy_slug).strip()
    description = str(spec.get("description") or "").strip()
    if not description:
        raise RuntimeError("strategy spec description is required")

    profile_payload = {
        "profile_name": normalized_profile,
        "status": profile_status or "candidate",
        "source": source,
        "overrides": profile_overrides if profile_overrides is not None else _default_profile_overrides(spec),
        "validation": {
            **(validation or {}),
            "definition_source": source,
            "strategy_name": name,
        },
    }

    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from strategy_specs where slug = %s", (strategy_slug,))
            if not cur.fetchone():
                raise RuntimeError(f"strategy not found: {strategy_slug}")
            cur.execute(
                """
                update strategy_specs
                set name = %s,
                    description = %s,
                    status = %s,
                    spec = %s,
                    updated_at = now()
                where slug = %s
                """,
                (
                    name,
                    description,
                    str(spec.get("status") or "draft"),
                    Json(spec),
                    strategy_slug,
                ),
            )
    db_service.upsert_profile(strategy_slug, profile_payload, is_active=activate_profile)
    return {
        "strategy_slug": strategy_slug,
        "profile_name": normalized_profile,
        "strategy": get_strategy(strategy_slug),
        "profile": profile_payload,
    }


def scaffold_strategy_definition(strategy_slug: str, profile_name: str | None = None) -> dict[str, Any]:
    db_service = _db_service()
    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    scaffold = _default_strategy_spec(strategy_slug, spec)
    db_service.init_schema()
    resolved_profile = profile["profile_name"]
    profile_payload = {
        "profile_name": resolved_profile,
        "status": "generated",
        "source": profile.get("source") or "web_scaffold",
        "overrides": _default_profile_overrides(scaffold),
        "validation": {
            **(profile.get("validation") or {}),
            "scaffold_note_zh": "工作台生成的基础策略定义，用于打通流程；正式研究前需要人工或 AI 复核。",
        },
    }
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update strategy_specs
                set name = %s,
                    description = %s,
                    status = 'draft',
                    spec = %s,
                    updated_at = now()
                where slug = %s
                """,
                (
                    scaffold.get("name", strategy_slug),
                    scaffold.get("description"),
                    Json(scaffold),
                    strategy_slug,
                ),
            )
    db_service.upsert_profile(strategy_slug, profile_payload, is_active=False)
    return {
        "strategy_slug": strategy_slug,
        "profile_name": resolved_profile,
        "spec": scaffold,
        "profile": profile_payload,
        "scaffold_explanation": _strategy_scaffold_explanation(scaffold),
    }


def scaffold_profile_defaults(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    db_service = _db_service()
    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    if not _has_executable_definition(spec):
        spec = _default_strategy_spec(strategy_slug, spec)
        scaffold_strategy_definition(strategy_slug, profile_name)
    profile_payload = {
        "profile_name": profile["profile_name"],
        "status": profile.get("status") if profile.get("status") != "draft" else "generated",
        "source": profile.get("source") or "web_profile_scaffold",
        "overrides": _default_profile_overrides(spec),
        "validation": {
            **(profile.get("validation") or {}),
            "profile_scaffold_note_zh": "工作台按当前 spec 生成的默认参数档案。",
        },
    }
    db_service.upsert_profile(strategy_slug, profile_payload, is_active=False)
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "profile": profile_payload,
        "profile_explanation": _profile_scaffold_explanation(profile_payload["overrides"]),
    }


def update_profile_overrides(
    strategy_slug: str,
    profile_name: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(overrides, dict) or not overrides:
        raise RuntimeError("profile overrides are required")

    protected_statuses = {"validated", "paper_active", "live_candidate", "live_active", "archived"}
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select status, validation
                from strategy_profiles
                where strategy_slug = %s and profile_name = %s
                """,
                (strategy_slug, profile_name),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"profile not found: {strategy_slug}/{profile_name}")
            if row["status"] in protected_statuses:
                raise RuntimeError(f"profile status {row['status']} is protected; create a new draft profile before editing")

            validation = row.get("validation") or {}
            validation["last_manual_edit_zh"] = "工作台手工编辑 overrides；未自动晋级状态。"
            cur.execute(
                """
                update strategy_profiles
                set overrides = %s,
                    validation = %s,
                    updated_at = now()
                where strategy_slug = %s and profile_name = %s
                returning profile_name, status, source, is_active, overrides, validation, created_at, updated_at
                """,
                (Json(overrides), Json(validation), strategy_slug, profile_name),
            )
            profile = dict(cur.fetchone())
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "profile": profile,
    }


def _strategy_scaffold_explanation(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "warning_zh": "这是流程打通模板，不是可直接实盘策略；正式研究前必须人工或 AI 复核因子、规则、风控和样本外结果。",
        "factors": spec.get("factors") or {},
        "entry_conditions": spec.get("entry_conditions") or {},
        "exit_conditions": spec.get("exit_conditions") or {},
        "timeranges": {
            "train": spec.get("train_timerange"),
            "validation": spec.get("validation_timerange"),
            "test": spec.get("test_timerange"),
        },
        "risk_model": spec.get("risk_model") or {},
        "trade_controls": {
            "minimal_roi": spec.get("minimal_roi"),
            "stoploss": spec.get("stoploss"),
            "trailing_stop": spec.get("trailing_stop"),
            "trailing_stop_positive": spec.get("trailing_stop_positive"),
            "trailing_stop_positive_offset": spec.get("trailing_stop_positive_offset"),
        },
    }


def _profile_scaffold_explanation(overrides: dict[str, Any]) -> dict[str, Any]:
    return {
        "warning_zh": "默认参数只用于让工作台流程可运行，不代表经过调优或验证。",
        "overrides": overrides,
        "editable_fields_zh": [
            "max_open_trades",
            "stoploss",
            "trailing_stop_positive",
            "trailing_stop_positive_offset",
            "minimal_roi",
            "核心 factor 参数",
        ],
    }


def _default_strategy_spec(strategy_slug: str, current: dict[str, Any]) -> dict[str, Any]:
    name = current.get("name") or strategy_slug
    description = current.get("description") or f"{name} 基础策略定义"
    return {
        **current,
        "name": name,
        "description": description,
        "version": current.get("version", "0.1"),
        "status": "draft",
        "timeframe": current.get("timeframe", "15m"),
        "trading_mode": current.get("trading_mode", "futures"),
        "margin_mode": current.get("margin_mode", "isolated"),
        "can_short": current.get("can_short", True),
        "train_timerange": current.get("train_timerange", "20250101-20250930"),
        "validation_timerange": current.get("validation_timerange", "20251001-20251130"),
        "test_timerange": current.get("test_timerange", "20251201-"),
        "cost_model": current.get("cost_model", {"fee": 0.001, "slippage_bps": 6, "funding_rate_included": False}),
        "risk_model": current.get(
            "risk_model",
            {
                "max_open_trades": 3,
                "max_drawdown_pct": 18.0,
                "max_daily_loss_pct": 3.0,
                "max_consecutive_losses": 4,
                "cooldown_candles_after_loss_streak": 8,
                "protections_in_config_required": True,
            },
        ),
        "minimal_roi": current.get("minimal_roi", {"0": 0.018, "120": 0.006, "360": 0.0}),
        "stoploss": current.get("stoploss", -0.08),
        "trailing_stop": current.get("trailing_stop", True),
        "trailing_stop_positive": current.get("trailing_stop_positive", 0.009),
        "trailing_stop_positive_offset": current.get("trailing_stop_positive_offset", 0.016),
        "optimization": current.get(
            "optimization",
            {"epochs": 120, "timerange": "20250101-20250930", "hyperopt_loss": "ShortTradeDurHyperOptLoss"},
        ),
        "factors": current.get(
            "factors",
            {
                "ma": {"enabled": True, "type": "EMA", "period": 72, "range": [30, 120], "space": "buy"},
                "rsi": {"enabled": True, "period": 14, "range": [7, 28], "space": "buy"},
                "rsi_oversold": {"enabled": True, "value": 31, "range": [18, 40], "space": "buy"},
                "rsi_overbought": {"enabled": True, "value": 69, "range": [60, 88], "space": "sell"},
                "volume": {"enabled": True, "ma_period": 24, "ratio_threshold": 1.0, "ratio_range": [0.5, 2.5]},
            },
        ),
        "entry_conditions": current.get(
            "entry_conditions",
            {
                "long": "(dataframe['close'] > dataframe['ma']) & (dataframe['rsi'] <= rsi_oversold) & (dataframe['volume_ratio'] >= volume_ratio_threshold)",
                "short": "(dataframe['close'] < dataframe['ma']) & (dataframe['rsi'] >= rsi_overbought) & (dataframe['volume_ratio'] >= volume_ratio_threshold)",
            },
        ),
        "exit_conditions": current.get(
            "exit_conditions",
            {
                "long": "(dataframe['close'] < dataframe['ma']) | (dataframe['rsi'] >= 55)",
                "short": "(dataframe['close'] > dataframe['ma']) | (dataframe['rsi'] <= 45)",
            },
        ),
    }


def _default_profile_overrides(spec: dict[str, Any]) -> dict[str, Any]:
    factors = spec.get("factors") or {}
    factor_overrides: dict[str, Any] = {}
    for factor_name, factor in factors.items():
        if not isinstance(factor, dict):
            continue
        values = {
            key: factor[key]
            for key in ["period", "value", "std", "ma_period", "ratio_threshold"]
            if key in factor
        }
        if values:
            factor_overrides[factor_name] = values
    return {
        "factors": factor_overrides,
        "risk_model": {"max_open_trades": (spec.get("risk_model") or {}).get("max_open_trades", 3)},
        "minimal_roi": spec.get("minimal_roi", {"0": 0.018, "120": 0.006, "360": 0.0}),
        "stoploss": spec.get("stoploss", -0.08),
        "trailing_stop": spec.get("trailing_stop", True),
        "trailing_stop_positive": spec.get("trailing_stop_positive", 0.009),
        "trailing_stop_positive_offset": spec.get("trailing_stop_positive_offset", 0.016),
    }


def _has_executable_definition(spec: dict[str, Any]) -> bool:
    return all(
        [
            isinstance(spec.get("factors"), dict) and bool(spec.get("factors")),
            isinstance(spec.get("entry_conditions"), dict) and bool(spec.get("entry_conditions")),
            isinstance(spec.get("exit_conditions"), dict) and bool(spec.get("exit_conditions")),
            bool(spec.get("train_timerange")),
            bool(spec.get("validation_timerange")),
            bool(spec.get("test_timerange")),
            isinstance(spec.get("risk_model"), dict) and bool(spec.get("risk_model")),
        ]
    )


def _validate_strategy_spec_executable(strategy_slug: str, spec: dict[str, Any]) -> None:
    _validate_condition_expressions(spec)
    generation_service, _runtime_service, _spec_service = _strategy_service_modules()
    try:
        code = generation_service.generate_strategy(strategy_slug, spec)
        compile(code, f"<strategy:{strategy_slug}>", "exec")
    except Exception as exc:
        raise RuntimeError(f"strategy spec failed generation validation: {type(exc).__name__}: {exc}") from exc


def _validate_condition_expressions(spec: dict[str, Any]) -> None:
    for section_name in ["entry_conditions", "exit_conditions"]:
        conditions = spec.get(section_name) or {}
        if not isinstance(conditions, dict):
            raise RuntimeError(f"{section_name} must be an object")
        for side, expression in conditions.items():
            if not isinstance(expression, str) or not expression.strip():
                raise RuntimeError(f"{section_name}.{side} must be a non-empty expression string")
            normalized = expression.strip()
            if normalized in {"False", "false", "0", "True", "true", "1"}:
                continue
            try:
                tree = ast.parse(normalized, mode="eval")
            except SyntaxError as exc:
                raise RuntimeError(f"{section_name}.{side} is not valid Python expression: {exc.msg}") from exc
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "dataframe":
                    if not _is_string_subscript(node.slice):
                        raise RuntimeError(f"{section_name}.{side} uses dataframe[...] without a quoted column name")


def _is_string_subscript(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Index):  # pragma: no cover - compatibility with older Python ASTs
        return _is_string_subscript(node.value)
    return False


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
