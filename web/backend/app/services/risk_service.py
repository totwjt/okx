from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.services.paper_service import _safe_api_get
from app.services.system_check import PROJECT_ROOT


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
RUNTIME_STRATEGY_DIR = PROJECT_ROOT / "execution/freqtrade/user_data/runtime_strategies"


def _load_strategy_services() -> Any:
    import sys

    strategy_dir = PROJECT_ROOT / "strategies"
    if str(strategy_dir) not in sys.path:
        sys.path.insert(0, str(strategy_dir))

    from services import db_service

    return db_service


def _latest_runtime_artifact() -> dict[str, Any]:
    candidates = sorted(RUNTIME_STRATEGY_DIR.glob("auto_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {"ok": False, "error": "runtime artifact json not found"}

    artifact_path = candidates[0]
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "path": str(artifact_path), "error": str(exc)}

    strategy_slug = artifact_path.stem.removeprefix("auto_")
    return {
        "ok": True,
        "path": str(artifact_path),
        "strategy_slug": strategy_slug,
        "strategy_name": data.get("strategy_name"),
        "profile_name": data.get("profile_name"),
        "export_time": data.get("export_time"),
    }


def _effective_risk_model(strategy_slug: str, profile_name: str | None) -> dict[str, Any]:
    db_service = _load_strategy_services()
    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    risk_model = dict(spec.get("risk_model") or {})
    risk_model.update((profile.get("overrides") or {}).get("risk_model") or {})
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile.get("profile_name"),
        "profile_status": profile.get("status"),
        "risk_model": risk_model,
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _closed_trades(trades_payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not trades_payload.get("ok") or not isinstance(trades_payload.get("data"), dict):
        return []
    trades = trades_payload["data"].get("trades", []) or []
    return [trade for trade in trades if not trade.get("is_open")]


def _consecutive_losses(closed_trades: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(closed_trades, key=lambda trade: int(trade.get("close_timestamp") or 0), reverse=True)
    count = 0
    for trade in ordered:
        profit = _as_float(trade.get("profit_abs", trade.get("close_profit_abs")))
        if profit < 0:
            count += 1
            continue
        break
    return {
        "count": count,
        "sample_size": len(ordered),
        "latest_closed_trade_id": ordered[0].get("trade_id") if ordered else None,
        "latest_closed_at": ordered[0].get("close_date") if ordered else None,
    }


def _daily_loss(closed_trades: list[dict[str, Any]], balance_payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(LOCAL_TZ)
    day_start = datetime.combine(now.date(), time.min, tzinfo=LOCAL_TZ)
    day_start_ms = int(day_start.astimezone(timezone.utc).timestamp() * 1000)
    today_trades = [trade for trade in closed_trades if int(trade.get("close_timestamp") or 0) >= day_start_ms]
    realized = sum(_as_float(trade.get("profit_abs", trade.get("close_profit_abs"))) for trade in today_trades)
    loss_abs = abs(min(realized, 0.0))

    balance_total = 0.0
    if balance_payload.get("ok") and isinstance(balance_payload.get("data"), dict):
        balance_total = _as_float(balance_payload["data"].get("total_bot") or balance_payload["data"].get("total"))

    return {
        "date": now.date().isoformat(),
        "timezone": str(LOCAL_TZ),
        "realized_pnl_abs": realized,
        "loss_abs": loss_abs,
        "loss_ratio": loss_abs / balance_total if balance_total > 0 else 0.0,
        "closed_trades": len(today_trades),
        "balance_basis": balance_total,
    }


def _rule_status(observed: float, limit: float | None) -> str:
    if limit is None:
        return "unknown"
    return "breach" if observed > limit else "ok"


def risk_summary() -> dict[str, Any]:
    artifact = _latest_runtime_artifact()
    rules: dict[str, Any] = {}
    bundle: dict[str, Any] = {}
    rule_error = None

    if artifact.get("ok"):
        try:
            bundle = _effective_risk_model(artifact["strategy_slug"], artifact.get("profile_name"))
            rules = bundle["risk_model"]
        except Exception as exc:
            rule_error = str(exc)

    profit = _safe_api_get("profit")
    trades = _safe_api_get("trades?limit=100")
    balance = _safe_api_get("balance")
    locks = _safe_api_get("locks")

    closed_trades = _closed_trades(trades)
    daily = _daily_loss(closed_trades, balance)
    loss_streak = _consecutive_losses(closed_trades)

    profit_data = profit.get("data") if profit.get("ok") and isinstance(profit.get("data"), dict) else {}
    max_drawdown_ratio = _as_float(profit_data.get("max_drawdown"))
    current_drawdown_ratio = _as_float(profit_data.get("current_drawdown"))
    max_drawdown_limit = _as_float(rules.get("max_drawdown_pct"), -1.0)
    daily_loss_limit = _as_float(rules.get("max_daily_loss_pct"), -1.0)
    loss_streak_limit = int(_as_float(rules.get("max_consecutive_losses"), -1.0))

    max_drawdown_limit_ratio = max_drawdown_limit / 100 if max_drawdown_limit >= 0 else None
    daily_loss_limit_ratio = daily_loss_limit / 100 if daily_loss_limit >= 0 else None
    loss_streak_limit_value = loss_streak_limit if loss_streak_limit >= 0 else None
    cooldown_candles = int(_as_float(rules.get("cooldown_candles_after_loss_streak"), 0))

    lock_rows = []
    if locks.get("ok") and isinstance(locks.get("data"), dict):
        lock_rows = locks["data"].get("locks", []) or []

    risk_checks = [
        {
            "key": "max_drawdown",
            "label": "Max drawdown",
            "observed": max_drawdown_ratio,
            "limit": max_drawdown_limit_ratio,
            "status": _rule_status(max_drawdown_ratio, max_drawdown_limit_ratio),
        },
        {
            "key": "daily_loss",
            "label": "Daily loss",
            "observed": daily["loss_ratio"],
            "limit": daily_loss_limit_ratio,
            "status": _rule_status(daily["loss_ratio"], daily_loss_limit_ratio),
        },
        {
            "key": "consecutive_losses",
            "label": "Consecutive losses",
            "observed": loss_streak["count"],
            "limit": loss_streak_limit_value,
            "status": _rule_status(float(loss_streak["count"]), float(loss_streak_limit_value) if loss_streak_limit_value is not None else None),
        },
        {
            "key": "cooldown",
            "label": "Cooldown",
            "observed": len(lock_rows),
            "limit": cooldown_candles,
            "status": "active" if lock_rows else "standby",
        },
    ]

    return {
        "ok": bool(artifact.get("ok") and not rule_error and profit.get("ok")),
        "mode": "read-only",
        "source": {
            "runtime_artifact": artifact,
            "rule_error": rule_error,
            "freqtrade_profit_ok": profit.get("ok", False),
            "freqtrade_trades_ok": trades.get("ok", False),
            "freqtrade_locks_ok": locks.get("ok", False),
        },
        "strategy": {
            "slug": bundle.get("strategy_slug"),
            "profile_name": bundle.get("profile_name"),
            "profile_status": bundle.get("profile_status"),
            "strategy_name": artifact.get("strategy_name"),
        },
        "rules": {
            "max_drawdown_pct": rules.get("max_drawdown_pct"),
            "max_daily_loss_pct": rules.get("max_daily_loss_pct"),
            "max_consecutive_losses": rules.get("max_consecutive_losses"),
            "cooldown_candles_after_loss_streak": rules.get("cooldown_candles_after_loss_streak"),
            "max_open_trades": rules.get("max_open_trades"),
            "protections_in_config_required": rules.get("protections_in_config_required"),
        },
        "metrics": {
            "max_drawdown_ratio": max_drawdown_ratio,
            "max_drawdown_abs": _as_float(profit_data.get("max_drawdown_abs")),
            "current_drawdown_ratio": current_drawdown_ratio,
            "current_drawdown_abs": _as_float(profit_data.get("current_drawdown_abs")),
            "daily_loss": daily,
            "consecutive_losses": loss_streak,
            "cooldown": {
                "configured_candles": cooldown_candles,
                "active_locks": len(lock_rows),
                "locks": lock_rows,
            },
        },
        "checks": risk_checks,
        "recent_closed_trades": sorted(closed_trades, key=lambda trade: int(trade.get("close_timestamp") or 0), reverse=True)[:12],
        "errors": {
            "profit": profit.get("error"),
            "trades": trades.get("error"),
            "balance": balance.get("error"),
            "locks": locks.get("error"),
        },
    }
