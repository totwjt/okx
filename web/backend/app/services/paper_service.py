from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from app.services.system_check import FREQTRADE_API_URL, FREQTRADE_CONFIG, _check_freqtrade


API_AUTH = "freqtrade:freqtrade"


def _api_get(path: str, timeout: int = 8) -> dict[str, Any] | list[Any]:
    token = base64.b64encode(API_AUTH.encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        f"{FREQTRADE_API_URL.rstrip('/')}/api/v1/{path.lstrip('/')}",
        headers={"Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_api_get(path: str) -> dict[str, Any]:
    try:
        return {"ok": True, "data": _api_get(path)}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def paper_summary() -> dict[str, Any]:
    config = json.loads(FREQTRADE_CONFIG.read_text(encoding="utf-8"))
    freqtrade = _check_freqtrade()
    ping = _safe_api_get("ping")
    status = _safe_api_get("status")
    balance = _safe_api_get("balance")
    profit = _safe_api_get("profit")
    trades = _safe_api_get("trades?limit=8")

    api_ok = bool(ping["ok"] and ping.get("data", {}).get("status") == "pong")
    open_trades = status.get("data") if status.get("ok") and isinstance(status.get("data"), list) else []
    trade_rows = []
    if trades.get("ok") and isinstance(trades.get("data"), dict):
        trade_rows = trades["data"].get("trades", []) or []

    return {
        "ok": bool(freqtrade.get("ok") and api_ok),
        "mode": "dry-run",
        "execution_baseline": "REST",
        "websocket_enabled": bool(config.get("exchange", {}).get("enable_ws")),
        "dry_run": bool(config.get("dry_run")),
        "trading_mode": config.get("trading_mode"),
        "margin_mode": config.get("margin_mode"),
        "pair_whitelist": config.get("exchange", {}).get("pair_whitelist", []),
        "freqtrade": freqtrade,
        "api": {
            "ok": api_ok,
            "url": FREQTRADE_API_URL,
            "ping": ping,
        },
        "balance": balance,
        "profit": profit,
        "open_trades": {
            "ok": status.get("ok", False),
            "count": len(open_trades),
            "items": open_trades,
            "error": status.get("error"),
        },
        "recent_trades": {
            "ok": trades.get("ok", False),
            "items": trade_rows[-8:],
            "error": trades.get("error"),
        },
    }
