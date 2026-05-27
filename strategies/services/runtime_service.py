import json
import os
from datetime import datetime, timezone
from pathlib import Path


STRATEGY_DIR = Path(os.getenv("STRATEGY_SOURCE_DIR", Path(__file__).resolve().parents[1]))


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_project_path(value: str | None, default: str) -> Path:
    path = Path(value or default)
    if path.is_absolute():
        return path
    return project_root() / path


RUNTIME_STRATEGY_DIR = resolve_project_path(
    os.getenv("STRATEGY_RUNTIME_DIR"),
    "execution/freqtrade/user_data/runtime_strategies",
)
RUNTIME_PARAM_DIR = resolve_project_path(
    os.getenv("STRATEGY_PARAM_RUNTIME_DIR"),
    "execution/freqtrade/user_data/runtime_params",
)

FREQTRADE_FACTOR_PARAMS: tuple[tuple[str, str, str, str], ...] = (
    ("ma", "period", "ma_period", "buy"),
    ("rsi", "period", "rsi_period", "buy"),
    ("rsi_oversold", "value", "rsi_oversold", "buy"),
    ("rsi_overbought", "value", "rsi_overbought", "sell"),
    ("bb", "period", "bb_period", "buy"),
    ("bb", "std", "bb_std", "buy"),
    ("bb", "width_trend_min", "bb_width_trend_min", "buy"),
    ("bb", "width_range_max", "bb_width_range_max", "buy"),
    ("volume", "ma_period", "volume_ma_period", "buy"),
    ("volume", "ratio_threshold", "volume_ratio_threshold", "buy"),
    ("macd", "fast", "macd_fast", "buy"),
    ("macd", "slow", "macd_slow", "buy"),
    ("macd", "signal", "macd_signal", "buy"),
    ("adx", "period", "adx_period", "buy"),
    ("adx", "trend_min", "adx_trend_min", "buy"),
    ("adx", "range_max", "adx_range_max", "buy"),
    ("atr", "period", "atr_period", "buy"),
    ("atr", "entry_max", "atr_entry_max", "buy"),
    ("atr", "exit_max", "atr_exit_max", "sell"),
    ("zscore", "period", "zscore_period", "buy"),
    ("zscore", "entry_abs", "zscore_entry_abs", "buy"),
    ("zscore", "exit_abs", "zscore_exit_abs", "sell"),
    ("donchian", "period", "donchian_period", "buy"),
)


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
    for factor_name, factor_field, param_name, space in FREQTRADE_FACTOR_PARAMS:
        factor = factors.get(factor_name, {})
        if not factor.get("enabled") or factor_field not in factor:
            continue
        params[space][param_name] = factor[factor_field]
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
