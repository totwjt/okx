import json
import pprint
from pathlib import Path

from services.runtime_service import STRATEGY_DIR, strategy_class_name
from services.spec_service import build_protections


GENERATED_DIR = Path("/freqtrade/user_data/strategies/generated")


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

    if factors.get("rsi_overbought", {}).get("enabled", False):
        rsi_ob = factors["rsi_overbought"]
        params_code.append(
            f"    rsi_overbought = DecimalParameter({rsi_ob['range'][0]}, {rsi_ob['range'][1]}, default={rsi_ob['value']}, decimals=1, space=\"{rsi_ob.get('space', 'sell')}\")"
        )

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

    if factors.get("volume", {}).get("enabled", False):
        vol = factors["volume"]
        params_code.append(f"    volume_ma_period = IntParameter(10, 30, default={vol['ma_period']}, space=\"buy\")")
        params_code.append(
            f"    volume_ratio_threshold = DecimalParameter(1.0, 2.5, default={vol['ratio_threshold']}, decimals=1, space=\"buy\")"
        )
        indicators_code.append("        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()")
        indicators_code.append("        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']")

    if factors.get("macd", {}).get("enabled", False):
        macd = factors["macd"]
        params_code.append(f"    macd_fast = IntParameter(5, 15, default={macd['fast']}, space=\"buy\")")
        params_code.append(f"    macd_slow = IntParameter(15, 35, default={macd['slow']}, space=\"buy\")")
        params_code.append(f"    macd_signal = IntParameter(5, 15, default={macd['signal']}, space=\"buy\")")
        indicators_code.append(
            "        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)"
        )

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
