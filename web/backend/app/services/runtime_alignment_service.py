from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.paper_service import _safe_api_get
from app.services.system_check import FREQTRADE_CONFIG, PROJECT_ROOT, _load_strategy_services


RUNTIME_STRATEGY_DIR = PROJECT_ROOT / "execution/freqtrade/user_data/runtime_strategies"


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def _strategy_modules() -> tuple[Any, Any]:
    import sys

    strategy_dir = PROJECT_ROOT / "strategies"
    if str(strategy_dir) not in sys.path:
        sys.path.insert(0, str(strategy_dir))
    from services import runtime_service, spec_service

    return runtime_service, spec_service


def runtime_alignment(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    checks = []
    active_profile = _active_profile(strategy_slug)
    db_artifacts = _latest_db_artifacts(strategy_slug, profile_name)
    runtime_json = _runtime_json(strategy_slug)
    config = _config_summary()
    freqtrade = _freqtrade_summary()
    effective = _effective_runtime_expectation(strategy_slug, profile_name)

    checks.append(
        _check(
            "active_profile",
            "当前 active profile",
            active_profile == profile_name,
            f"active profile = {active_profile or '-'}，当前页面 profile = {profile_name}",
            {"active_profile": active_profile, "profile_name": profile_name},
        )
    )
    checks.append(
        _check(
            "runtime_artifacts",
            "最新 runtime artifact",
            bool(db_artifacts.get("freqtrade_strategy_py") and db_artifacts.get("freqtrade_params_json")),
            "数据库中存在策略和参数 runtime artifact 记录。"
            if db_artifacts.get("freqtrade_strategy_py") and db_artifacts.get("freqtrade_params_json")
            else "缺少策略或参数 runtime artifact 记录。",
            db_artifacts,
        )
    )
    checks.append(
        _check(
            "runtime_json_profile",
            "Runtime JSON profile",
            bool(runtime_json.get("ok") and runtime_json.get("profile_name") == profile_name),
            f"runtime JSON profile = {runtime_json.get('profile_name') or '-'}",
            runtime_json,
        )
    )
    checks.append(
        _check(
            "runtime_json_strategy",
            "Runtime JSON strategy",
            bool(runtime_json.get("ok") and runtime_json.get("strategy_slug") == strategy_slug),
            f"runtime JSON strategy = {runtime_json.get('strategy_slug') or '-'}",
            runtime_json,
        )
    )
    expected_class = effective.get("strategy_class")
    running_strategy = freqtrade.get("strategy")
    checks.append(
        _check(
            "freqtrade_strategy",
            "Freqtrade 当前策略",
            bool(running_strategy and expected_class and running_strategy == expected_class),
            f"Freqtrade strategy = {running_strategy or '-'}，期望 = {expected_class or '-'}",
            freqtrade,
            required=False if not freqtrade.get("ok") else True,
        )
    )
    expected_max_open = effective.get("max_open_trades")
    config_max_open = config.get("max_open_trades")
    checks.append(
        _check(
            "max_open_trades",
            "max_open_trades 一致性",
            expected_max_open is not None and config_max_open == expected_max_open,
            f"config max_open_trades = {config_max_open}，策略风险模型 = {expected_max_open}",
            {"config": config, "effective": effective},
        )
    )
    checks.append(
        _check(
            "config_hash",
            "Freqtrade config hash",
            bool(config.get("ok") and config.get("config_hash")),
            "已读取当前 Freqtrade config hash。" if config.get("ok") else str(config.get("error") or "config 读取失败"),
            config,
            required=False,
        )
    )

    required_failed = [check for check in checks if check["required"] and not check["passed"]]
    unknown = [check for check in checks if check["status"] == "unknown"]
    status = "aligned" if not required_failed else "drift"
    if unknown and not required_failed:
        status = "unknown"
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "ok": status == "aligned",
        "status": status,
        "summary_zh": "runtime 对齐" if status == "aligned" else "runtime 存在漂移" if status == "drift" else "runtime 状态未知",
        "blocked_reasons": [check["details_zh"] for check in required_failed],
        "checks": checks,
        "sources": {
            "active_profile": active_profile,
            "runtime_json": runtime_json,
            "config": config,
            "freqtrade": freqtrade,
            "effective": effective,
        },
    }


def _active_profile(strategy_slug: str) -> str | None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select profile_name
                from strategy_profiles
                where strategy_slug = %s and is_active
                limit 1
                """,
                (strategy_slug,),
            )
            row = cur.fetchone()
            return row["profile_name"] if row else None


def _latest_db_artifacts(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    db_service = _db_service()
    db_service.init_schema()
    artifacts: dict[str, Any] = {}
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select distinct on (artifact_type)
                  artifact_type, artifact_path, artifact_hash, metadata, created_at
                from strategy_runtime_artifacts
                where strategy_slug = %s and profile_name = %s
                order by artifact_type, created_at desc, id desc
                """,
                (strategy_slug, profile_name),
            )
            for row in cur.fetchall():
                artifacts[row["artifact_type"]] = dict(row)
    return artifacts


def _runtime_json(strategy_slug: str) -> dict[str, Any]:
    path = RUNTIME_STRATEGY_DIR / f"auto_{strategy_slug}.json"
    if not path.exists():
        return {"ok": False, "path": str(path), "error": "runtime params json not found"}
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
    return {
        "ok": True,
        "path": str(path),
        "strategy_slug": strategy_slug,
        "profile_name": data.get("profile_name"),
        "strategy_name": data.get("strategy_name"),
        "export_time": data.get("export_time"),
        "artifact_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _config_summary() -> dict[str, Any]:
    try:
        text = FREQTRADE_CONFIG.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "path": str(FREQTRADE_CONFIG), "error": str(exc)}
    return {
        "ok": True,
        "path": str(FREQTRADE_CONFIG),
        "config_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "max_open_trades": data.get("max_open_trades"),
        "dry_run": data.get("dry_run"),
        "trading_mode": data.get("trading_mode"),
        "strategy_path": data.get("strategy_path"),
    }


def _freqtrade_summary() -> dict[str, Any]:
    payload = _safe_api_get("show_config")
    if not payload.get("ok") or not isinstance(payload.get("data"), dict):
        return {"ok": False, "error": payload.get("error")}
    data = payload["data"]
    return {
        "ok": True,
        "strategy": data.get("strategy"),
        "strategy_version": data.get("strategy_version"),
        "max_open_trades": data.get("max_open_trades"),
        "dry_run": data.get("dry_run"),
    }


def _effective_runtime_expectation(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    runtime_service, spec_service = _strategy_modules()
    db_service = _db_service()
    try:
        spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
        effective = spec_service.apply_profile_overrides(spec, profile)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    risk_model = effective.get("risk_model") or {}
    return {
        "ok": True,
        "strategy_class": runtime_service.strategy_class_name(strategy_slug),
        "max_open_trades": risk_model.get("max_open_trades"),
        "profile_status": profile.get("status"),
    }


def _check(
    key: str,
    title_zh: str,
    passed: bool,
    details_zh: str,
    evidence: dict[str, Any],
    *,
    required: bool = True,
) -> dict[str, Any]:
    status = "passed" if passed else "failed"
    if not required and not passed:
        status = "unknown"
    return {
        "key": key,
        "title_zh": title_zh,
        "passed": passed,
        "required": required,
        "status": status,
        "details_zh": details_zh,
        "evidence": evidence,
    }
