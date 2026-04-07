import copy
import sys
from pathlib import Path

import yaml

from services.profile_service import load_profile


SPEC_DIR = Path("/freqtrade/user_data/strategies/spec")


def load_spec(name: str) -> dict:
    spec_file = SPEC_DIR / f"{name}.yaml"
    if not spec_file.exists():
        spec_file = SPEC_DIR / f"{name}.yml"

    if not spec_file.exists():
        print(f"错误: 找不到规范文件 {name}.yaml")
        sys.exit(1)

    with open(spec_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_profile_overrides(spec: dict, profile: dict) -> dict:
    merged = copy.deepcopy(spec)
    overrides = profile.get("overrides", {})
    for factor_name, fields in (overrides.get("factors", {}) or {}).items():
        merged.setdefault("factors", {}).setdefault(factor_name, {})
        merged["factors"][factor_name].update(fields or {})
    for key in [
        "stoploss",
        "minimal_roi",
        "trailing_stop",
        "trailing_stop_positive",
        "trailing_stop_positive_offset",
        "trailing_only_offset_is_reached",
    ]:
        if key in overrides:
            merged[key] = overrides[key]
    if "risk_model" in overrides:
        merged.setdefault("risk_model", {}).update(overrides["risk_model"] or {})
    return merged


def get_effective_spec(name: str, profile_name: str | None = None) -> tuple[dict, dict]:
    spec = load_spec(name)
    profile = load_profile(name, spec, profile_name)
    return apply_profile_overrides(spec, profile), profile


def get_timeranges(spec: dict) -> dict:
    optimization = spec.get("optimization", {})
    return {
        "train": spec.get("train_timerange") or optimization.get("timerange", "20250101-20250930"),
        "validation": spec.get("validation_timerange", "20251001-20251130"),
        "test": spec.get("test_timerange", "20251201-"),
    }


def get_cost_model(spec: dict) -> dict:
    return spec.get("cost_model", {})


def get_risk_model(spec: dict) -> dict:
    return spec.get("risk_model", {})


def build_protections(spec: dict) -> list[dict]:
    risk_model = get_risk_model(spec)
    protections = []

    cooldown = risk_model.get("cooldown_candles_after_loss_streak")
    if cooldown:
        protections.append(
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": int(cooldown),
            }
        )

    stoploss_trade_limit = risk_model.get("max_consecutive_losses")
    if stoploss_trade_limit:
        protections.append(
            {
                "method": "StoplossGuard",
                "lookback_period_candles": int(risk_model.get("stoploss_guard_lookback_candles", 96)),
                "trade_limit": int(stoploss_trade_limit),
                "stop_duration_candles": int(cooldown or 12),
                "only_per_pair": False,
            }
        )

    max_drawdown_pct = risk_model.get("max_drawdown_pct")
    if max_drawdown_pct is not None:
        protections.append(
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": int(risk_model.get("max_drawdown_lookback_candles", 96)),
                "trade_limit": int(risk_model.get("max_drawdown_trade_limit", 20)),
                "stop_duration_candles": int(cooldown or 12),
                "max_allowed_drawdown": float(max_drawdown_pct) / 100.0,
            }
        )

    return protections


def get_config_path(spec: dict) -> str:
    trading_mode = spec.get("trading_mode", "spot")
    config_path = "/freqtrade/user_data/config.json"
    if trading_mode == "futures":
        futures_config = "/freqtrade/user_data/config_futures.json"
        if Path(futures_config).exists():
            config_path = futures_config
    return config_path
