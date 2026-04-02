#!/usr/bin/env python3
import argparse
import copy
import json
import os
import pprint
import shutil
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone


STRATEGY_DIR = Path("/freqtrade/user_data/strategies")
SPEC_DIR = Path("/freqtrade/user_data/strategies/spec")
GENERATED_DIR = Path("/freqtrade/user_data/strategies/generated")
RESULTS_DIR = Path("/freqtrade/user_data/strategies/results")
PROFILE_ROOT_DIR = Path("/freqtrade/user_data/strategies/profiles")
PROFILE_BT_RESULT_DIR = Path("/freqtrade/user_data/backtest_results/profile_validation")
CONFIG_DIR = Path("/freqtrade/user_data/config.json")


def load_spec(name: str) -> dict:
    spec_file = SPEC_DIR / f"{name}.yaml"
    if not spec_file.exists():
        spec_file = SPEC_DIR / f"{name}.yml"
    
    if not spec_file.exists():
        print(f"错误: 找不到规范文件 {name}.yaml")
        sys.exit(1)
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


PARAM_FACTOR_MAP = {
    "ma_period": ("ma", "period"),
    "rsi_period": ("rsi", "period"),
    "rsi_oversold": ("rsi_oversold", "value"),
    "rsi_overbought": ("rsi_overbought", "value"),
}

PROFILE_DEFAULT_NAME = "default"


def strategy_class_name(name: str) -> str:
    return ''.join(word.capitalize() for word in name.replace('-', ' ').replace('_', ' ').split()) + 'Strategy'


def profile_dir(name: str) -> Path:
    return PROFILE_ROOT_DIR / name


def profile_path(name: str, profile_name: str) -> Path:
    return profile_dir(name) / f"{profile_name}.yaml"


def active_profile_path(name: str) -> Path:
    return profile_dir(name) / "_active.yaml"


def ensure_profile_dir(name: str) -> Path:
    pdir = profile_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def extract_default_overrides(spec: dict) -> dict:
    factors = spec.get("factors", {})
    factor_overrides: dict[str, dict] = {}
    for factor_name, field_name in PARAM_FACTOR_MAP.values():
        factor = factors.get(factor_name)
        if not factor:
            continue
        factor_overrides.setdefault(factor_name, {})
        if field_name in factor:
            factor_overrides[factor_name][field_name] = factor[field_name]

    overrides: dict[str, object] = {"factors": factor_overrides, "risk_model": {}}
    for key in [
        "stoploss",
        "minimal_roi",
        "trailing_stop",
        "trailing_stop_positive",
        "trailing_stop_positive_offset",
        "trailing_only_offset_is_reached",
    ]:
        if key in spec:
            overrides[key] = spec[key]
    risk_model = spec.get("risk_model", {})
    if "max_open_trades" in risk_model:
        overrides["risk_model"]["max_open_trades"] = risk_model["max_open_trades"]
    return overrides


def default_profile_payload(name: str, spec: dict, profile_name: str = PROFILE_DEFAULT_NAME) -> dict:
    return {
        "profile_name": profile_name,
        "strategy_name": name,
        "status": "draft",
        "source": "spec_defaults",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overrides": extract_default_overrides(spec),
    }


def ensure_default_profile(name: str, spec: dict) -> None:
    ensure_profile_dir(name)
    dpath = profile_path(name, PROFILE_DEFAULT_NAME)
    if not dpath.exists():
        with open(dpath, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_profile_payload(name, spec), f, allow_unicode=True, sort_keys=False)
    apath = active_profile_path(name)
    if not apath.exists():
        with open(apath, "w", encoding="utf-8") as f:
            yaml.safe_dump({"active_profile": PROFILE_DEFAULT_NAME}, f, allow_unicode=True, sort_keys=False)


def get_active_profile_name(name: str, spec: dict | None = None) -> str:
    if spec is not None:
        ensure_default_profile(name, spec)
    apath = active_profile_path(name)
    if not apath.exists():
        return PROFILE_DEFAULT_NAME
    with open(apath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("active_profile", PROFILE_DEFAULT_NAME)


def load_profile(name: str, spec: dict, profile_name: str | None = None) -> dict:
    ensure_default_profile(name, spec)
    resolved = profile_name or get_active_profile_name(name, spec)
    ppath = profile_path(name, resolved)
    if not ppath.exists():
        print(f"错误: 找不到 profile 文件 {resolved}.yaml")
        sys.exit(1)
    with open(ppath, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f) or {}
    profile.setdefault("profile_name", resolved)
    profile.setdefault("strategy_name", name)
    profile.setdefault("status", "draft")
    profile.setdefault("overrides", {})
    return profile


def save_profile(name: str, profile: dict) -> Path:
    ensure_profile_dir(name)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    ppath = profile_path(name, profile["profile_name"])
    with open(ppath, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, allow_unicode=True, sort_keys=False)
    return ppath


def set_active_profile(name: str, spec: dict, profile_name: str) -> None:
    ensure_default_profile(name, spec)
    ppath = profile_path(name, profile_name)
    if not ppath.exists():
        print(f"错误: profile 不存在: {profile_name}")
        sys.exit(1)
    with open(active_profile_path(name), "w", encoding="utf-8") as f:
        yaml.safe_dump({"active_profile": profile_name}, f, allow_unicode=True, sort_keys=False)


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


def build_profile_from_hyperopt(name: str, profile_name: str, hyperopt_filename: str, params: dict) -> dict:
    overrides = {
        "factors": {
            "ma": {"period": params["params"]["ma_period"]},
            "rsi": {"period": params["params"]["rsi_period"]},
            "rsi_oversold": {"value": params["params"]["rsi_oversold"]},
            "rsi_overbought": {"value": params["params"]["rsi_overbought"]},
        },
        "stoploss": params["stoploss"],
        "minimal_roi": params["minimal_roi"],
        "trailing_stop": params["trailing_stop"],
        "trailing_stop_positive": params["trailing_stop_positive"],
        "trailing_stop_positive_offset": params["trailing_stop_positive_offset"],
        "trailing_only_offset_is_reached": params["trailing_only_offset_is_reached"],
        "risk_model": {
            "max_open_trades": params["max_open_trades"],
        },
    }
    return {
        "profile_name": profile_name,
        "strategy_name": name,
        "status": "candidate",
        "source": f"hyperopt:{hyperopt_filename}",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overrides": overrides,
    }


def read_backtest_summary(zip_path: Path, strategy_name: str) -> dict:
    import zipfile

    with zipfile.ZipFile(zip_path) as z:
        json_member = next(
            (
                n for n in z.namelist()
                if n.endswith(".json") and "_config" not in n and "_signals" not in n and "_market_change" not in n
            ),
            None,
        )
        if not json_member:
            raise RuntimeError(f"Backtest zip missing result json: {zip_path}")
        payload = json.loads(z.read(json_member).decode("utf-8"))

    strategy_section = payload.get("strategy")
    if isinstance(strategy_section, dict):
        if strategy_name in strategy_section:
            return strategy_section[strategy_name]
        if len(strategy_section) == 1:
            return next(iter(strategy_section.values()))

    raise RuntimeError(f"Strategy metrics not found in backtest result: {zip_path}")


def latest_created_backtest_zip(before: set[str], result_dir: Path) -> Path:
    candidates = [p for p in result_dir.glob("*.zip") if p.name not in before]
    if not candidates:
        raise RuntimeError("未找到新的回测结果文件")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def normalize_backtest_metrics(metrics: dict) -> dict:
    total_trades = int(metrics.get("total_trades", 0) or 0)
    profit_total = float(metrics.get("profit_total", metrics.get("profit_total_ratio", 0)) or 0)
    profit_total_abs = float(metrics.get("profit_total_abs", 0) or 0)
    profit_factor = float(metrics.get("profit_factor", 0) or 0)

    drawdown_candidates = [
        metrics.get("max_drawdown_account"),
        metrics.get("max_drawdown"),
        metrics.get("absolute_drawdown"),
    ]
    max_drawdown = 0.0
    for value in drawdown_candidates:
        if value is not None:
            max_drawdown = float(value)
            break

    return {
        "total_trades": total_trades,
        "profit_total": profit_total,
        "profit_total_abs": profit_total_abs,
        "profit_factor": profit_factor,
        "max_drawdown_account": max_drawdown,
        "stake_currency": metrics.get("stake_currency", "USDT"),
    }


def get_config_path(spec: dict) -> str:
    trading_mode = spec.get('trading_mode', 'spot')
    config_path = "/freqtrade/user_data/config.json"
    if trading_mode == 'futures':
        futures_config = "/freqtrade/user_data/config_futures.json"
        if Path(futures_config).exists():
            config_path = futures_config
    return config_path


def ensure_generated_strategy(name: str, spec: dict) -> Path:
    code = generate_strategy(name, spec)
    output_file = GENERATED_DIR / f"{name}.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)

    strategy_file = STRATEGY_DIR / f"auto_{name}.py"
    with open(strategy_file, 'w', encoding='utf-8') as f:
        f.write(code)

    return output_file


def get_timeranges(spec: dict) -> dict:
    optimization = spec.get('optimization', {})
    return {
        "train": spec.get('train_timerange') or optimization.get('timerange', "20250101-20250930"),
        "validation": spec.get('validation_timerange', "20251001-20251130"),
        "test": spec.get('test_timerange', "20251201-"),
    }


def get_cost_model(spec: dict) -> dict:
    return spec.get('cost_model', {})


def get_risk_model(spec: dict) -> dict:
    return spec.get('risk_model', {})


def build_protections(spec: dict) -> list[dict]:
    risk_model = get_risk_model(spec)
    protections = []

    cooldown = risk_model.get('cooldown_candles_after_loss_streak')
    if cooldown:
        protections.append({
            "method": "CooldownPeriod",
            "stop_duration_candles": int(cooldown),
        })

    stoploss_trade_limit = risk_model.get('max_consecutive_losses')
    if stoploss_trade_limit:
        protections.append({
            "method": "StoplossGuard",
            "lookback_period_candles": int(risk_model.get('stoploss_guard_lookback_candles', 96)),
            "trade_limit": int(stoploss_trade_limit),
            "stop_duration_candles": int(cooldown or 12),
            "only_per_pair": False,
        })

    max_drawdown_pct = risk_model.get('max_drawdown_pct')
    if max_drawdown_pct is not None:
        protections.append({
            "method": "MaxDrawdown",
            "lookback_period_candles": int(risk_model.get('max_drawdown_lookback_candles', 96)),
            "trade_limit": int(risk_model.get('max_drawdown_trade_limit', 20)),
            "stop_duration_candles": int(cooldown or 12),
            "max_allowed_drawdown": float(max_drawdown_pct) / 100.0,
        })

    return protections


def run_backtest_phase(name: str, config_path: str, label: str, timerange: str):
    spec = load_spec(name)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    fee = cost_model.get('fee')
    print(f"\n[{label}] 回测")
    print(f"  时间范围: {timerange}")
    if fee is not None:
        print(f"  fee: {fee}")
    if risk_model.get('max_open_trades') is not None:
        print(f"  max_open_trades: {risk_model['max_open_trades']}")
    if risk_model.get('max_drawdown_pct') is not None:
        print(f"  max_drawdown_pct: {risk_model['max_drawdown_pct']}")
    cmd = f"freqtrade backtesting -c {config_path} -s {name} --timerange {timerange}"
    if fee is not None:
        cmd += f" --fee {fee}"
    if build_protections(spec):
        cmd += " --enable-protections"
    os.system(cmd)


def generate_strategy_v2(name: str, spec: dict) -> str:
    class_name = strategy_class_name(name)
    
    trading_mode = spec.get('trading_mode', 'spot')
    can_short = spec.get('can_short', False) if trading_mode == 'spot' else True
    timeframe = spec.get('timeframe', '15m')
    stoploss = spec.get('stoploss', -0.03)
    minimal_roi = spec.get('minimal_roi', {"0": 0.01})
    trailing_stop = spec.get('trailing_stop', True)
    trailing_stop_positive = spec.get('trailing_stop_positive', 0.01)
    trailing_stop_positive_offset = spec.get('trailing_stop_positive_offset', 0.015)
    
    added_params = set()
    params_code = []
    indicators_code = []
    
    factors = spec.get('factors', {})
    
    if factors.get('ma', {}).get('enabled', False):
        ma = factors['ma']
        param_name = 'ma_period'
        params_code.append(f"    {param_name} = IntParameter({ma['range'][0]}, {ma['range'][1]}, default={ma['period']}, space=\"{ma.get('space', 'buy')}\")")
        added_params.add(param_name)
        ma_type = ma.get('type', 'SMA')
        indicators_code.append(f"        dataframe['ma'] = ta.{ma_type}(dataframe['close'], timeperiod=self.ma_period.value)")
    
    if factors.get('rsi', {}).get('enabled', False):
        rsi = factors['rsi']
        param_name = 'rsi_period'
        params_code.append(f"    {param_name} = IntParameter({rsi['range'][0]}, {rsi['range'][1]}, default={rsi['period']}, space=\"{rsi.get('space', 'buy')}\")")
        added_params.add(param_name)
        indicators_code.append(f"        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)")
    
    if factors.get('rsi_oversold', {}).get('enabled', False):
        rsi_os = factors['rsi_oversold']
        params_code.append(f"    rsi_oversold = DecimalParameter({rsi_os['range'][0]}, {rsi_os['range'][1]}, default={rsi_os['value']}, decimals=1, space=\"{rsi_os.get('space', 'buy')}\")")
        added_params.add('rsi_oversold')
    
    if factors.get('rsi_overbought', {}).get('enabled', False):
        rsi_ob = factors['rsi_overbought']
        params_code.append(f"    rsi_overbought = DecimalParameter({rsi_ob['range'][0]}, {rsi_ob['range'][1]}, default={rsi_ob['value']}, decimals=1, space=\"{rsi_ob.get('space', 'sell')}\")")
        added_params.add('rsi_overbought')
    
    if factors.get('bb', {}).get('enabled', False):
        bb = factors['bb']
        params_code.append(f"    bb_period = IntParameter(10, 50, default={bb['period']}, space=\"buy\")")
        added_params.add('bb_period')
        std_range = bb.get('std_range', [1.5, 3.0])
        params_code.append(f"    bb_std = DecimalParameter({std_range[0]}, {std_range[1]}, default={bb.get('std', 2.0)}, decimals=1, space=\"buy\")")
        added_params.add('bb_std')
        indicators_code.append(f"        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)")
    
    if factors.get('volume', {}).get('enabled', False):
        vol = factors['volume']
        params_code.append(f"    volume_ma_period = IntParameter(10, 30, default={vol['ma_period']}, space=\"buy\")")
        added_params.add('volume_ma_period')
        params_code.append(f"    volume_ratio_threshold = DecimalParameter(1.0, 2.5, default={vol['ratio_threshold']}, decimals=1, space=\"buy\")")
        added_params.add('volume_ratio_threshold')
        indicators_code.append(f"        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()")
        indicators_code.append(f"        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']")
    
    if factors.get('macd', {}).get('enabled', False):
        macd = factors['macd']
        params_code.append(f"    macd_fast = IntParameter(5, 15, default={macd['fast']}, space=\"buy\")")
        params_code.append(f"    macd_slow = IntParameter(15, 35, default={macd['slow']}, space=\"buy\")")
        params_code.append(f"    macd_signal = IntParameter(5, 15, default={macd['signal']}, space=\"buy\")")
        indicators_code.append(f"        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)")
    
    for ind in spec.get('derived_indicators', []):
        ind_name = ind['name']
        formula = ind.get('formula', '')
        indicators_code.append(f"        dataframe['{ind_name}'] = {formula}")
    
    entry = spec.get('entry_conditions', {})
    long_entry = entry.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_entry = entry.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    exit_cond = spec.get('exit_conditions', {})
    long_exit = exit_cond.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_exit = exit_cond.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    protections = pprint.pformat(build_protections(spec), indent=8, sort_dicts=False)
    
    code = f'''"""
{spec.get('description', name)} V{spec.get('version', '1.0')} - Auto-generated strategy
Trading Mode: {trading_mode}
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class {class_name}(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = {can_short}
    timeframe = "{timeframe}"
    
    stoploss = {stoploss}
    minimal_roi = {json.dumps(minimal_roi)}
    
    trailing_stop = {trailing_stop}
    trailing_stop_positive = {trailing_stop_positive}
    trailing_stop_positive_offset = {trailing_stop_positive_offset}
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
{chr(10).join(params_code)}
    
    startup_candle_count = 300
    
    order_types = {{
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }}
    
    order_time_in_force = {{"entry": "GTC", "exit": "GTC"}}

    @property
    def protections(self):
        return {protections}
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
{chr(10).join(indicators_code)}
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        long_condition = {long_entry}
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = {short_entry}
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
'''
    
    return code


def generate_strategy(name: str, spec: dict) -> str:
    return generate_strategy_v2(name, spec)
    
    can_short = spec.get('can_short', False)
    timeframe = spec.get('timeframe', '15m')
    stoploss = spec.get('stoploss', -0.03)
    minimal_roi = spec.get('minimal_roi', {"0": 0.01})
    trailing_stop = spec.get('trailing_stop', True)
    trailing_stop_positive = spec.get('trailing_stop_positive', 0.01)
    trailing_stop_positive_offset = spec.get('trailing_stop_positive_offset', 0.015)
    
    added_params = set()
    params_code = []
    indicators_code = []
    
    for ind in spec.get('indicators', []):
        ind_name = ind['name'].lower()
        ind_type = ind.get('type', 'SMA')
        params = ind.get('params', [10, 50, 20])
        
        if ind_type in ['SMA', 'EMA', 'WMA']:
            param_name = f"{ind_name}_period"
            if param_name not in added_params:
                params_code.append(f"    {param_name} = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add(param_name)
            indicators_code.append(f"        dataframe['{ind_name}'] = ta.{ind_type}(dataframe['close'], timeperiod=self.{param_name}.value)")
        elif ind_type == 'RSI':
            param_name = f"{ind_name}_period"
            if param_name not in added_params:
                params_code.append(f"    {param_name} = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add(param_name)
            indicators_code.append(f"        dataframe['{ind_name}'] = ta.RSI(dataframe['close'], timeperiod=self.{param_name}.value)")
        elif ind_type == 'BB':
            if 'bb_period' not in added_params:
                params_code.append(f"    bb_period = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add('bb_period')
            std_params = ind.get('std', [1.5, 3.0, 2.0])
            if 'bb_std' not in added_params:
                params_code.append(f"    bb_std = DecimalParameter({std_params[0]}, {std_params[1]}, default={std_params[2]}, decimals=1, space=\"buy\")")
                added_params.add('bb_std')
            indicators_code.append(f"        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)")
    
    for ind in spec.get('derived_indicators', []):
        ind_name = ind['name']
        formula = ind.get('formula', '')
        indicators_code.append(f"        dataframe['{ind_name}'] = {formula}")
    
    entry = spec.get('entry_conditions', {})
    long_entry = entry.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_entry = entry.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    exit_cond = spec.get('exit_conditions', {})
    long_exit = exit_cond.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_exit = exit_cond.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    params = spec.get('params', {})
    for pname, pdata in params.items():
        if pname not in added_params:
            if 'rsi_oversold' in pname or 'rsi_overbought' in pname:
                params_code.append(f"    {pname} = DecimalParameter({pdata['min']}, {pdata['max']}, default={pdata['default']}, decimals=1, space=\"buy\" if 'oversold' in '{pname}' else \"sell\")")
            else:
                params_code.append(f"    {pname} = IntParameter({pdata['min']}, {pdata['max']}, default={pdata['default']}, space=\"buy\")")
            added_params.add(pname)
    
    code = f'''"""
{spec.get('description', name)} - Auto-generated strategy
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class {class_name}(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = {can_short}
    timeframe = "{timeframe}"
    
    stoploss = {stoploss}
    minimal_roi = {json.dumps(minimal_roi)}
    
    trailing_stop = {trailing_stop}
    trailing_stop_positive = {trailing_stop_positive}
    trailing_stop_positive_offset = {trailing_stop_positive_offset}
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
{chr(10).join(params_code)}
    
    startup_candle_count = 300
    
    order_types = {{
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }}
    
    order_time_in_force = {{"entry": "GTC", "exit": "GTC"}}
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
{chr(10).join(indicators_code)}
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        long_condition = {long_entry}
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = {short_entry}
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
'''
    
    return code


def cmd_list(args):
    """列出所有策略"""
    print("\n=== 策略规范 ===")
    for f in sorted(SPEC_DIR.glob("*.yaml")):
        print(f"  - {f.stem}")
    
    print("\n=== 已生成策略 ===")
    for f in sorted(GENERATED_DIR.glob("*.py")):
        print(f"  - {f.stem}")

    print("\n=== Profiles ===")
    for f in sorted(SPEC_DIR.glob("*.yaml")):
        name = f.stem
        spec = load_spec(name)
        ensure_default_profile(name, spec)
        active = get_active_profile_name(name, spec)
        profiles = sorted(
            [p.stem for p in profile_dir(name).glob("*.yaml") if not p.name.startswith("_")]
        )
        print(f"  - {name}: active={active}, profiles={profiles}")
    
    print()


def cmd_generate(args):
    name = args.name
    print(f"生成策略: {name}")
    
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    output_file = ensure_generated_strategy(name, spec)
    runtime_json = sync_runtime_profile(name, spec, profile)
    
    print(f"  生成完成: {output_file}")
    print(f"  复制到: {STRATEGY_DIR / f'auto_{name}.py'}")
    print(f"  运行参数快照: {runtime_json}")
    print(f"  使用 profile: {profile['profile_name']}")
    print(f"\n  当前仓库以 strategies/ 为单一策略源码目录，无需额外 docker cp 同步。")


def cmd_backtest(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    timeranges = get_timeranges(spec)
    phase = args.phase or "train"
    timerange = args.timerange or timeranges[phase]
    config_path = get_config_path(spec)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    
    print(f"运行回测: {name}")
    print(f"  阶段: {phase}")
    print(f"  时间范围: {timerange}")
    if cost_model.get('fee') is not None:
        print(f"  fee: {cost_model['fee']}")
    if cost_model.get('slippage_bps') is not None:
        print(f"  slippage_bps: {cost_model['slippage_bps']} (当前未自动注入 Freqtrade CLI)")
    if cost_model.get('funding_rate_included') is False:
        print(f"  funding_rate: 未纳入")
    if risk_model:
        print(f"  风控边界: max_open_trades={risk_model.get('max_open_trades')}, max_daily_loss_pct={risk_model.get('max_daily_loss_pct')}, max_drawdown_pct={risk_model.get('max_drawdown_pct')}")
    
    cmd = f"freqtrade backtesting -c {config_path} -s {name} --timerange {timerange}"
    if cost_model.get('fee') is not None:
        cmd += f" --fee {cost_model['fee']}"
    if build_protections(spec):
        cmd += " --enable-protections"
    os.system(cmd)


def cmd_validate(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    config_path = get_config_path(spec)
    timeranges = get_timeranges(spec)

    print(f"运行分段验证: {name}")
    print(f"  train: {timeranges['train']}")
    print(f"  validation: {timeranges['validation']}")
    print(f"  test: {timeranges['test']}")

    for phase in ["train", "validation", "test"]:
        run_backtest_phase(name, config_path, phase.upper(), timeranges[phase])


def cmd_optimize(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    opt_config = spec.get('optimization', {})
    epochs = args.epochs or opt_config.get('epochs', 200)
    timerange = args.timerange or spec.get('train_timerange') or opt_config.get('timerange', "20250101-20250930")
    config_path = get_config_path(spec)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    
    print(f"运行参数优化: {name}")
    print(f"  迭代次数: {epochs}")
    print(f"  时间范围: {timerange}")
    print(f"  阶段: train")
    if cost_model.get('fee') is not None:
        print(f"  fee: {cost_model['fee']}")
    if risk_model:
        print(f"  风控边界: max_open_trades={risk_model.get('max_open_trades')}, max_daily_loss_pct={risk_model.get('max_daily_loss_pct')}, max_drawdown_pct={risk_model.get('max_drawdown_pct')}")
    
    cmd = f"freqtrade hyperopt -c {config_path} -s {name} --timerange {timerange} --epochs {epochs} -j 4"
    if opt_config.get('hyperopt_loss'):
        cmd += f" --hyperopt-loss {opt_config['hyperopt_loss']}"
    if cost_model.get('fee') is not None:
        cmd += f" --fee {cost_model['fee']}"
    if build_protections(spec):
        cmd += " --enable-protections"
    
    os.system(cmd)
    
    result_file = STRATEGY_DIR / f"auto_{name}.json"
    if result_file.exists():
        print(f"\n优化参数已保存到: {result_file}")


def cmd_run(args):
    """运行完整流程"""
    name = args.name
    
    print(f"=== 运行完整流程: {name} ===\n")
    
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    print("[1/4] 生成策略...")
    output_file = ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    print(f"  完成: {output_file}\n")
    
    opt_config = spec.get('optimization', {})
    epochs = opt_config.get('epochs', 200)
    timeranges = get_timeranges(spec)
    config_path = get_config_path(spec)
    
    print(f"[2/4] 训练集参数优化 (epochs={epochs})...")
    cmd = f"freqtrade hyperopt -c {config_path} -s {name} --timerange {timeranges['train']} --epochs {epochs} -j 4"
    if opt_config.get('hyperopt_loss'):
        cmd += f" --hyperopt-loss {opt_config['hyperopt_loss']}"
    if build_protections(spec):
        cmd += " --enable-protections"
    os.system(cmd)
    print()
    
    print("[3/4] 验证集回测...")
    run_backtest_phase(name, config_path, "VALIDATION", timeranges['validation'])
    
    print("\n[4/4] 测试集回测...")
    run_backtest_phase(name, config_path, "TEST", timeranges['test'])
    
    print("\n=== 完成 ===")


def cmd_config(args):
    name = args.name
    
    spec = load_spec(name)
    ensure_default_profile(name, spec)
    active_profile = load_profile(name, spec)
    
    if args.list:
        print(f"\n=== {name} 配置 ===")
        print(f"\nActive profile: {active_profile['profile_name']} ({active_profile.get('status', 'draft')})")
        print(f"\n交易模式: {spec.get('trading_mode', 'spot')}")
        print(f"时间框架: {spec.get('timeframe')}")
        print(f"支持做空: {spec.get('can_short')}")
        
        print("\n--- 因子配置 ---")
        factors = spec.get('factors', {})
        for fname, fconfig in factors.items():
            if fconfig.get('enabled', False):
                print(f"\n{fname}:")
                if 'range' in fconfig:
                    print(f"  范围: {fconfig['range']}")
                if 'value' in fconfig:
                    print(f"  默认值: {fconfig['value']}")
                if 'period' in fconfig:
                    print(f"  周期: {fconfig['period']}")
        
        print("\n--- 当前默认参数基线 ---")
        factors = spec.get('factors', {})
        for key, (factor_name, field_name) in PARAM_FACTOR_MAP.items():
            factor = factors.get(factor_name, {})
            if field_name in factor:
                print(f"  {key}: {factor[field_name]}")

        print("\n--- 当前 active profile 覆盖值 ---")
        pprint.pprint(active_profile.get("overrides", {}), sort_dicts=False)

        print("\n--- 风控模型 ---")
        risk_model = get_risk_model(spec)
        for key, value in risk_model.items():
            if key != "notes":
                print(f"  {key}: {value}")
        
        print()
        return
    
    if args.set:
        key, value = args.set
        try:
            value = float(value)
        except ValueError:
            pass
        
        if key not in PARAM_FACTOR_MAP:
            print(f"错误: 暂不支持设置参数 {key}")
            print(f"支持的参数: {', '.join(PARAM_FACTOR_MAP.keys())}")
            sys.exit(1)

        factor_name, field_name = PARAM_FACTOR_MAP[key]
        if 'factors' not in spec or factor_name not in spec['factors']:
            print(f"错误: 规范中找不到参数对应的因子 {factor_name}")
            sys.exit(1)

        spec['factors'][factor_name][field_name] = value
        
        spec_file = SPEC_DIR / f"{name}.yaml"
        with open(spec_file, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, allow_unicode=True, default_flow_style=False)
        save_profile(name, default_profile_payload(name, spec))
        
        print(f"已设置默认参数 {key} = {value}")
        print("请重新生成策略: generate", name)
        return
    
    print(f"用法:")
    print(f"  python cli.py config {name} --list      # 列出配置")
    print(f"  python cli.py config {name} --set ma_period 200  # 设置参数")


def cmd_profile(args):
    name = args.name
    spec = load_spec(name)
    ensure_default_profile(name, spec)

    if args.profile_command == "list":
        active = get_active_profile_name(name, spec)
        print(f"\n=== {name} profiles ===")
        for p in sorted([p.stem for p in profile_dir(name).glob("*.yaml") if not p.name.startswith("_")]):
            profile = load_profile(name, spec, p)
            mark = "*" if p == active else " "
            print(f"{mark} {p}  status={profile.get('status', 'draft')}  source={profile.get('source', '-')}")
        print()
        return

    if args.profile_command == "show":
        profile = load_profile(name, spec, args.profile_name)
        pprint.pprint(profile, sort_dicts=False)
        return

    if args.profile_command == "create":
        from_profile_name = args.from_profile or get_active_profile_name(name, spec)
        source_profile = load_profile(name, spec, from_profile_name)
        new_profile = copy.deepcopy(source_profile)
        new_profile["profile_name"] = args.profile_name
        new_profile["status"] = "candidate"
        new_profile["source"] = f"profile:{from_profile_name}"
        ppath = save_profile(name, new_profile)
        print(f"已创建 profile: {ppath}")
        return

    if args.profile_command == "activate":
        profile = load_profile(name, spec, args.profile_name)
        set_active_profile(name, spec, args.profile_name)
        runtime_json = sync_runtime_profile(name, apply_profile_overrides(spec, profile), profile)
        print(f"已激活 profile: {args.profile_name}")
        print(f"运行参数快照: {runtime_json}")
        return

    if args.profile_command == "promote":
        profile = load_profile(name, spec, args.profile_name)
        profile["status"] = args.to_status
        save_profile(name, profile)
        if args.to_status in {"paper_active", "live_active"}:
            set_active_profile(name, spec, args.profile_name)
            runtime_json = sync_runtime_profile(name, apply_profile_overrides(spec, profile), profile)
            print(f"已晋级并激活 profile: {args.profile_name} -> {args.to_status}")
            print(f"运行参数快照: {runtime_json}")
            return
        print(f"已晋级 profile: {args.profile_name} -> {args.to_status}")
        return

    if args.profile_command == "import-hyperopt":
        result = subprocess.run(
            [
                "freqtrade",
                "hyperopt-show",
                "-c",
                str(CONFIG_DIR),
                "--hyperopt-filename",
                args.hyperopt_filename,
                "--best",
                "--print-json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        json_line = None
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                json_line = line
                break
        if not json_line:
            print("错误: 未能从 hyperopt-show 输出中解析 JSON 参数")
            sys.exit(1)
        params = json.loads(json_line)
        profile = build_profile_from_hyperopt(
            name,
            args.profile_name,
            args.hyperopt_filename,
            params,
        )
        ppath = save_profile(name, profile)
        print(f"已从 hyperopt 结果导入 candidate profile: {ppath}")
        return

    if args.profile_command == "validate":
        profile = load_profile(name, spec, args.profile_name)
        effective_spec = apply_profile_overrides(spec, profile)
        ensure_generated_strategy(name, effective_spec)
        sync_runtime_profile(name, effective_spec, profile)

        timeranges = get_timeranges(effective_spec)
        timerange = args.timerange or timeranges["validation"]
        config_path = get_config_path(effective_spec)
        cost_model = get_cost_model(effective_spec)
        PROFILE_BT_RESULT_DIR.mkdir(parents=True, exist_ok=True)
        before = {p.name for p in PROFILE_BT_RESULT_DIR.glob("*.zip")}

        cmd = [
            "freqtrade",
            "backtesting",
            "-c",
            config_path,
            "-s",
            strategy_class_name(name),
            "--timerange",
            timerange,
            "--export",
            "trades",
            "--backtest-directory",
            str(PROFILE_BT_RESULT_DIR),
        ]
        if cost_model.get("fee") is not None:
            cmd.extend(["--fee", str(cost_model["fee"])])
        if build_protections(effective_spec):
            cmd.append("--enable-protections")

        subprocess.run(cmd, check=True)

        try:
            latest_zip = latest_created_backtest_zip(before, PROFILE_BT_RESULT_DIR)
            metrics = normalize_backtest_metrics(read_backtest_summary(latest_zip, strategy_class_name(name)))
        except RuntimeError as exc:
            print(f"错误: {exc}")
            sys.exit(1)

        min_trades = args.min_trades
        min_profit = args.min_profit
        min_profit_factor = args.min_profit_factor
        max_drawdown_limit = args.max_drawdown

        passed = (
            metrics["total_trades"] >= min_trades
            and metrics["profit_total"] >= min_profit
            and metrics["profit_factor"] >= min_profit_factor
            and metrics["max_drawdown_account"] <= max_drawdown_limit
        )

        print(f"Validation profile: {profile['profile_name']}")
        print(f"Timerange: {timerange}")
        print(f"Backtest result: {latest_zip}")
        print(f"total_trades={metrics['total_trades']}")
        print(f"profit_total={metrics['profit_total']:.6f}")
        print(f"profit_total_abs={metrics['profit_total_abs']:.6f} {metrics['stake_currency']}")
        print(f"profit_factor={metrics['profit_factor']:.4f}")
        print(f"max_drawdown_account={metrics['max_drawdown_account']:.4f}")
        print(
            f"Gate: min_trades>={min_trades}, min_profit>={min_profit}, "
            f"min_profit_factor>={min_profit_factor}, max_drawdown<={max_drawdown_limit}"
        )
        print(f"Validation status: {'PASS' if passed else 'FAIL'}")

        profile.setdefault("validation", {})
        profile["validation"]["last_result"] = {
            "timerange": timerange,
            "backtest_zip": str(latest_zip),
            "metrics": metrics,
            "gate": {
                "min_trades": min_trades,
                "min_profit": min_profit,
                "min_profit_factor": min_profit_factor,
                "max_drawdown": max_drawdown_limit,
            },
            "passed": passed,
        }
        if passed and args.promote_on_pass:
            profile["status"] = "validated"
        save_profile(name, profile)
        if passed and args.promote_on_pass:
            print(f"已自动晋级 profile -> validated: {profile['profile_name']}")
        if not passed:
            sys.exit(2)
        return

    print("支持的 profile 子命令: list/show/create/activate/promote/import-hyperopt/validate")


def main():
    parser = argparse.ArgumentParser(description="策略管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    subparsers.add_parser("list", help="列出所有策略")
    
    gen_parser = subparsers.add_parser("generate", help="生成策略代码")
    gen_parser.add_argument("name", help="策略名称")
    gen_parser.add_argument("--profile", help="使用指定 profile 生成运行快照")
    
    bt_parser = subparsers.add_parser("backtest", help="运行回测")
    bt_parser.add_argument("name", help="策略名称")
    bt_parser.add_argument("--timerange", "-t", help="时间范围")
    bt_parser.add_argument("--phase", choices=["train", "validation", "test"], help="使用 YAML 中的阶段时间范围")
    bt_parser.add_argument("--profile", help="使用指定 profile")
    
    validate_parser = subparsers.add_parser("validate", help="运行 train/validation/test 分段回测")
    validate_parser.add_argument("name", help="策略名称")
    validate_parser.add_argument("--profile", help="使用指定 profile")
    
    opt_parser = subparsers.add_parser("optimize", help="运行参数优化")
    opt_parser.add_argument("name", help="策略名称")
    opt_parser.add_argument("--epochs", "-e", type=int, help="迭代次数")
    opt_parser.add_argument("--timerange", "-t", help="时间范围")
    opt_parser.add_argument("--profile", help="使用指定 profile")
    
    run_parser = subparsers.add_parser("run", help="运行完整流程")
    run_parser.add_argument("name", help="策略名称")
    run_parser.add_argument("--profile", help="使用指定 profile")
    
    config_parser = subparsers.add_parser("config", help="查看/修改策略配置")
    config_parser.add_argument("name", help="策略名称")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="设置参数")
    config_parser.add_argument("--list", action="store_true", help="列出所有参数")

    profile_parser = subparsers.add_parser("profile", help="管理策略 profiles 与 promotion")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", help="profile 子命令")

    profile_list = profile_subparsers.add_parser("list", help="列出所有 profiles")
    profile_list.add_argument("name", help="策略名称")

    profile_show = profile_subparsers.add_parser("show", help="查看 profile 内容")
    profile_show.add_argument("name", help="策略名称")
    profile_show.add_argument("profile_name", nargs="?", help="profile 名称，默认 active")

    profile_create = profile_subparsers.add_parser("create", help="从现有 profile 复制创建 candidate")
    profile_create.add_argument("name", help="策略名称")
    profile_create.add_argument("profile_name", help="新 profile 名称")
    profile_create.add_argument("--from-profile", help="复制来源 profile，默认 active")

    profile_activate = profile_subparsers.add_parser("activate", help="激活 profile")
    profile_activate.add_argument("name", help="策略名称")
    profile_activate.add_argument("profile_name", help="profile 名称")

    profile_promote = profile_subparsers.add_parser("promote", help="晋级 profile 状态")
    profile_promote.add_argument("name", help="策略名称")
    profile_promote.add_argument("profile_name", help="profile 名称")
    profile_promote.add_argument("to_status", choices=["candidate", "validated", "paper_active", "live_active"], help="目标状态")

    profile_import = profile_subparsers.add_parser("import-hyperopt", help="从 hyperopt 结果导入 candidate profile")
    profile_import.add_argument("name", help="策略名称")
    profile_import.add_argument("profile_name", help="新 candidate profile 名称")
    profile_import.add_argument("hyperopt_filename", help="hyperopt 结果文件名")

    profile_validate = profile_subparsers.add_parser("validate", help="跑 validation timerange 回测并评估 profile gate")
    profile_validate.add_argument("name", help="策略名称")
    profile_validate.add_argument("profile_name", nargs="?", help="profile 名称，默认 active")
    profile_validate.add_argument("--timerange", "-t", help="覆盖 validation_timerange")
    profile_validate.add_argument("--min-trades", type=int, default=1, help="最低成交笔数")
    profile_validate.add_argument("--min-profit", type=float, default=0.0, help="最低 profit_total")
    profile_validate.add_argument("--min-profit-factor", type=float, default=1.0, help="最低 profit_factor")
    profile_validate.add_argument("--max-drawdown", type=float, default=0.30, help="允许的最大回撤比例")
    profile_validate.add_argument("--promote-on-pass", action="store_true", help="验证通过后自动晋级为 validated")
    
    args = parser.parse_args()
    
    if args.command == "list":
        cmd_list(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "optimize":
        cmd_optimize(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "profile":
        cmd_profile(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
