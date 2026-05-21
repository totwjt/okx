import json
import os
import pprint
from pathlib import Path

from services.runtime_service import STRATEGY_DIR, strategy_class_name
from services.spec_service import build_protections


GENERATED_DIR = Path(os.getenv("STRATEGY_GENERATED_DIR", STRATEGY_DIR / "generated"))


def ensure_generated_strategy(name: str, spec: dict) -> Path:
    code = generate_strategy(name, spec)
    output_file = GENERATED_DIR / f"{name}.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)

    strategy_file = STRATEGY_DIR / f"auto_{name}.py"
    with open(strategy_file, "w", encoding="utf-8") as f:
        f.write(code)

    return output_file


def generate_strategy(name: str, spec: dict) -> str:
    return generate_strategy_v2(name, spec)


def generate_strategy_v2(name: str, spec: dict) -> str:
    class_name = strategy_class_name(name)

    trading_mode = spec.get("trading_mode", "spot")
    can_short = spec.get("can_short", False) if trading_mode == "spot" else True
    timeframe = spec.get("timeframe", "15m")
    stoploss = spec.get("stoploss", -0.03)
    minimal_roi = spec.get("minimal_roi", {"0": 0.01})
    trailing_stop = spec.get("trailing_stop", True)
    trailing_stop_positive = spec.get("trailing_stop_positive", 0.01)
    trailing_stop_positive_offset = spec.get("trailing_stop_positive_offset", 0.015)

    params_code = []
    indicators_code = []
    entry_aliases: list[tuple[str, object]] = []
    exit_aliases: list[tuple[str, object]] = []

    factors = spec.get("factors", {})

    if factors.get("ma", {}).get("enabled", False):
        ma = factors["ma"]
        params_code.append(
            f"    ma_period = IntParameter({ma['range'][0]}, {ma['range'][1]}, default={ma['period']}, space=\"{ma.get('space', 'buy')}\")"
        )
        ma_type = ma.get("type", "SMA")
        indicators_code.append(f"        dataframe['ma'] = ta.{ma_type}(dataframe['close'], timeperiod=self.ma_period.value)")

    if factors.get("rsi", {}).get("enabled", False):
        rsi = factors["rsi"]
        params_code.append(
            f"    rsi_period = IntParameter({rsi['range'][0]}, {rsi['range'][1]}, default={rsi['period']}, space=\"{rsi.get('space', 'buy')}\")"
        )
        indicators_code.append("        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)")

    if factors.get("rsi_oversold", {}).get("enabled", False):
        rsi_os = factors["rsi_oversold"]
        params_code.append(
            f"    rsi_oversold = DecimalParameter({rsi_os['range'][0]}, {rsi_os['range'][1]}, default={rsi_os['value']}, decimals=1, space=\"{rsi_os.get('space', 'buy')}\")"
        )
        entry_aliases.append(("rsi_oversold", rsi_os["value"]))
        exit_aliases.append(("rsi_oversold", rsi_os["value"]))

    if factors.get("rsi_overbought", {}).get("enabled", False):
        rsi_ob = factors["rsi_overbought"]
        params_code.append(
            f"    rsi_overbought = DecimalParameter({rsi_ob['range'][0]}, {rsi_ob['range'][1]}, default={rsi_ob['value']}, decimals=1, space=\"{rsi_ob.get('space', 'sell')}\")"
        )
        entry_aliases.append(("rsi_overbought", rsi_ob["value"]))
        exit_aliases.append(("rsi_overbought", rsi_ob["value"]))

    if factors.get("bb", {}).get("enabled", False):
        bb = factors["bb"]
        params_code.append(f"    bb_period = IntParameter(10, 50, default={bb['period']}, space=\"buy\")")
        std_range = bb.get("std_range", [1.5, 3.0])
        params_code.append(
            f"    bb_std = DecimalParameter({std_range[0]}, {std_range[1]}, default={bb.get('std', 2.0)}, decimals=1, space=\"buy\")"
        )
        indicators_code.append(
            "        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)"
        )
        if "width_trend_min" in bb:
            width_trend_range = bb.get("width_trend_range", [0.015, 0.05])
            params_code.append(
                f"    bb_width_trend_min = DecimalParameter({width_trend_range[0]}, {width_trend_range[1]}, default={bb['width_trend_min']}, decimals=3, space=\"buy\")"
            )
            entry_aliases.append(("bb_width_trend_min", bb["width_trend_min"]))
            exit_aliases.append(("bb_width_trend_min", bb["width_trend_min"]))
        if "width_range_max" in bb:
            width_range_max = bb.get("width_range_max_range", [0.01, 0.04])
            params_code.append(
                f"    bb_width_range_max = DecimalParameter({width_range_max[0]}, {width_range_max[1]}, default={bb['width_range_max']}, decimals=3, space=\"buy\")"
            )
            entry_aliases.append(("bb_width_range_max", bb["width_range_max"]))
            exit_aliases.append(("bb_width_range_max", bb["width_range_max"]))

    if factors.get("volume", {}).get("enabled", False):
        vol = factors["volume"]
        params_code.append(f"    volume_ma_period = IntParameter(10, 30, default={vol['ma_period']}, space=\"buy\")")
        ratio_range = vol.get("ratio_range", [0.5, 2.5])
        params_code.append(
            f"    volume_ratio_threshold = DecimalParameter({ratio_range[0]}, {ratio_range[1]}, default={vol['ratio_threshold']}, decimals=2, space=\"buy\")"
        )
        indicators_code.append("        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()")
        indicators_code.append("        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']")
        entry_aliases.append(("volume_ratio_threshold", vol["ratio_threshold"]))
        exit_aliases.append(("volume_ratio_threshold", vol["ratio_threshold"]))

    if factors.get("macd", {}).get("enabled", False):
        macd = factors["macd"]
        params_code.append(f"    macd_fast = IntParameter(5, 15, default={macd['fast']}, space=\"buy\")")
        params_code.append(f"    macd_slow = IntParameter(15, 35, default={macd['slow']}, space=\"buy\")")
        params_code.append(f"    macd_signal = IntParameter(5, 15, default={macd['signal']}, space=\"buy\")")
        indicators_code.append(
            "        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)"
        )

    if factors.get("adx", {}).get("enabled", False):
        adx = factors["adx"]
        adx_period_range = adx.get("period_range", [7, 28])
        trend_min_range = adx.get("trend_min_range", [18, 35])
        range_max_range = adx.get("range_max_range", [8, 22])
        params_code.append(
            f"    adx_period = IntParameter({adx_period_range[0]}, {adx_period_range[1]}, default={adx.get('period', 14)}, space=\"buy\")"
        )
        params_code.append(
            f"    adx_trend_min = DecimalParameter({trend_min_range[0]}, {trend_min_range[1]}, default={adx['trend_min']}, decimals=1, space=\"buy\")"
        )
        params_code.append(
            f"    adx_range_max = DecimalParameter({range_max_range[0]}, {range_max_range[1]}, default={adx['range_max']}, decimals=1, space=\"buy\")"
        )
        indicators_code.append("        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.adx_period.value)")
        entry_aliases.append(("adx_trend_min", adx["trend_min"]))
        entry_aliases.append(("adx_range_max", adx["range_max"]))
        exit_aliases.append(("adx_trend_min", adx["trend_min"]))
        exit_aliases.append(("adx_range_max", adx["range_max"]))

    if factors.get("atr", {}).get("enabled", False):
        atr = factors["atr"]
        atr_period_range = atr.get("period_range", [7, 28])
        atr_entry_range = atr.get("entry_max_range", [0.015, 0.06])
        atr_exit_range = atr.get("exit_max_range", [0.02, 0.08])
        params_code.append(
            f"    atr_period = IntParameter({atr_period_range[0]}, {atr_period_range[1]}, default={atr.get('period', 14)}, space=\"buy\")"
        )
        params_code.append(
            f"    atr_entry_max = DecimalParameter({atr_entry_range[0]}, {atr_entry_range[1]}, default={atr['entry_max']}, decimals=3, space=\"buy\")"
        )
        params_code.append(
            f"    atr_exit_max = DecimalParameter({atr_exit_range[0]}, {atr_exit_range[1]}, default={atr['exit_max']}, decimals=3, space=\"sell\")"
        )
        indicators_code.append("        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.atr_period.value)")
        indicators_code.append("        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'].replace(0, np.nan)")
        entry_aliases.append(("atr_entry_max", atr["entry_max"]))
        exit_aliases.append(("atr_exit_max", atr["exit_max"]))

    if factors.get("zscore", {}).get("enabled", False):
        zscore = factors["zscore"]
        zscore_period_range = zscore.get("period_range", [12, 72])
        entry_abs_range = zscore.get("entry_abs_range", [0.6, 2.2])
        exit_abs_range = zscore.get("exit_abs_range", [0.1, 1.2])
        params_code.append(
            f"    zscore_period = IntParameter({zscore_period_range[0]}, {zscore_period_range[1]}, default={zscore.get('period', 32)}, space=\"buy\")"
        )
        params_code.append(
            f"    zscore_entry_abs = DecimalParameter({entry_abs_range[0]}, {entry_abs_range[1]}, default={zscore['entry_abs']}, decimals=2, space=\"buy\")"
        )
        params_code.append(
            f"    zscore_exit_abs = DecimalParameter({exit_abs_range[0]}, {exit_abs_range[1]}, default={zscore['exit_abs']}, decimals=2, space=\"sell\")"
        )
        indicators_code.append("        dataframe['zscore_mean'] = dataframe['close'].rolling(self.zscore_period.value).mean()")
        indicators_code.append("        dataframe['zscore_std'] = dataframe['close'].rolling(self.zscore_period.value).std()")
        indicators_code.append("        dataframe['zscore'] = (dataframe['close'] - dataframe['zscore_mean']) / dataframe['zscore_std'].replace(0, np.nan)")
        entry_aliases.append(("zscore_entry_abs", zscore["entry_abs"]))
        exit_aliases.append(("zscore_exit_abs", zscore["exit_abs"]))

    if factors.get("donchian", {}).get("enabled", False):
        donchian = factors["donchian"]
        donchian_period_range = donchian.get("period_range", [10, 55])
        params_code.append(
            f"    donchian_period = IntParameter({donchian_period_range[0]}, {donchian_period_range[1]}, default={donchian.get('period', 20)}, space=\"buy\")"
        )
        indicators_code.append("        dataframe['donchian_high'] = dataframe['high'].rolling(self.donchian_period.value).max()")
        indicators_code.append("        dataframe['donchian_low'] = dataframe['low'].rolling(self.donchian_period.value).min()")

    entry_alias_code = [
        f"        {name} = self.{name}.value if hasattr(self, '{name}') else {repr(default)}"
        for name, default in entry_aliases
    ]
    exit_alias_code = [
        f"        {name} = self.{name}.value if hasattr(self, '{name}') else {repr(default)}"
        for name, default in exit_aliases
    ]

    for ind in spec.get("derived_indicators", []):
        indicators_code.append(f"        dataframe['{ind['name']}'] = {ind.get('formula', '')}")

    entry = spec.get("entry_conditions", {})
    long_entry = entry.get("long", "False").replace("\n", " ").replace("  ", " ")
    short_entry = entry.get("short", "False").replace("\n", " ").replace("  ", " ")

    exit_cond = spec.get("exit_conditions", {})
    long_exit = exit_cond.get("long", "False").replace("\n", " ").replace("  ", " ")
    short_exit = exit_cond.get("short", "False").replace("\n", " ").replace("  ", " ")
    protections = pprint.pformat(build_protections(spec), indent=8, sort_dicts=False)

    return f'''"""
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

{chr(10).join(entry_alias_code)}

        long_condition = {long_entry}
        dataframe.loc[long_condition, 'enter_long'] = 1

        short_condition = {short_entry}
        dataframe.loc[short_condition, 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

{chr(10).join(exit_alias_code)}

        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1

        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1

        return dataframe
'''
