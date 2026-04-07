import json
from datetime import datetime, timezone
from pathlib import Path


STRATEGY_DIR = Path("/freqtrade/user_data/strategies")


def strategy_class_name(name: str) -> str:
    return "".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split()) + "Strategy"


def build_freqtrade_params(name: str, spec: dict, profile_name: str | None = None) -> dict:
    factors = spec.get("factors", {})
    risk_model = spec.get("risk_model", {})
    params: dict[str, dict] = {
        "max_open_trades": {"max_open_trades": risk_model.get("max_open_trades", 3)},
        "buy": {},
        "sell": {},
        "roi": spec.get("minimal_roi", {"0": 0.01}),
        "stoploss": {"stoploss": spec.get("stoploss", -0.03)},
        "trailing": {
            "trailing_stop": spec.get("trailing_stop", True),
            "trailing_stop_positive": spec.get("trailing_stop_positive", 0.01),
            "trailing_stop_positive_offset": spec.get("trailing_stop_positive_offset", 0.015),
        },
    }
    if spec.get("trailing_only_offset_is_reached") is not None:
        params["trailing"]["trailing_only_offset_is_reached"] = spec["trailing_only_offset_is_reached"]
    if factors.get("ma", {}).get("enabled"):
        params["buy"]["ma_period"] = factors["ma"].get("period")
    if factors.get("rsi", {}).get("enabled"):
        params["buy"]["rsi_period"] = factors["rsi"].get("period")
    if factors.get("rsi_oversold", {}).get("enabled"):
        params["buy"]["rsi_oversold"] = factors["rsi_oversold"].get("value")
    if factors.get("rsi_overbought", {}).get("enabled"):
        params["sell"]["rsi_overbought"] = factors["rsi_overbought"].get("value")
    return {
        "strategy_name": strategy_class_name(name),
        "profile_name": profile_name,
        "params": params,
        "ft_stratparam_v": 1,
        "export_time": datetime.now(timezone.utc).isoformat(),
    }


def sync_runtime_profile(name: str, effective_spec: dict, profile: dict) -> Path:
    runtime_json_path = STRATEGY_DIR / f"auto_{name}.json"
    with open(runtime_json_path, "w", encoding="utf-8") as f:
        json.dump(
            build_freqtrade_params(name, effective_spec, profile.get("profile_name")),
            f,
            ensure_ascii=False,
            indent=2,
        )
    return runtime_json_path
