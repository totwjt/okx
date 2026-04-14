"""
网格均值回归策略 V1（RangeGrid + TrendPullback，支持标的波动变体） V1.1 - Dynamic baseline grid
Trading Mode: futures
"""

import numpy as np
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class GridLsV1Strategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "15m"

    stoploss = -0.11
    minimal_roi = {"0": 0.0322, "60": 0.0118, "240": 0.0}

    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.02

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # legacy params kept for profile compatibility
    ma_period = IntParameter(30, 120, default=54, space="buy")
    rsi_period = IntParameter(7, 28, default=11, space="buy")
    rsi_oversold = DecimalParameter(18, 40, default=34.0, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(60, 88, default=66.0, decimals=1, space="sell")
    bb_period = IntParameter(10, 50, default=38, space="buy")
    bb_std = DecimalParameter(1.6, 3.2, default=1.9, decimals=1, space="buy")
    volume_ma_period = IntParameter(10, 30, default=16, space="buy")
    volume_ratio_threshold = DecimalParameter(0.5, 2.5, default=0.9, decimals=1, space="buy")

    # dynamic baseline/grid params
    baseline_slow_period = IntParameter(80, 240, default=120, space="buy")
    baseline_weight = DecimalParameter(0.2, 0.9, default=0.55, decimals=2, space="buy")
    baseline_shift_atr_mult = DecimalParameter(0.0, 1.5, default=0.45, decimals=2, space="buy")
    trend_bias_threshold = DecimalParameter(0.0005, 0.01, default=0.0050, decimals=4, space="buy")

    grid_atr_mult = DecimalParameter(0.6, 2.5, default=1.15, decimals=2, space="buy")
    grid_entry_level = DecimalParameter(0.4, 2.5, default=1.2, decimals=2, space="buy")
    grid_exit_level = DecimalParameter(0.1, 2.0, default=0.45, decimals=2, space="sell")
    breakout_grid_level = DecimalParameter(0.6, 2.5, default=1.2, decimals=2, space="buy")

    startup_candle_count = 300

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 8},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 96,
                "trade_limit": 4,
                "stop_duration_candles": 8,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 20,
                "stop_duration_candles": 8,
                "max_allowed_drawdown": 0.18,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=self.rsi_period.value)
        dataframe["bb_upper"], dataframe["bb_middle"], dataframe["bb_lower"] = ta.BBANDS(
            dataframe["close"],
            timeperiod=self.bb_period.value,
            nbdevup=self.bb_std.value,
            nbdevdn=self.bb_std.value,
        )
        dataframe["volume_ma"] = dataframe["volume"].rolling(window=self.volume_ma_period.value).mean()
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_ma"].replace(0, np.nan)

        dataframe["ema_fast"] = ta.EMA(dataframe["close"], timeperiod=self.ma_period.value)
        dataframe["ema_slow"] = ta.EMA(dataframe["close"], timeperiod=self.baseline_slow_period.value)
        dataframe["adx"] = ta.ADX(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"].replace(0, np.nan)

        dataframe["trend_bias"] = (dataframe["ema_fast"] - dataframe["ema_slow"]) / dataframe["close"].replace(0, np.nan)
        trend_den = max(self.trend_bias_threshold.value, 1e-6)
        dataframe["trend_score"] = np.tanh(dataframe["trend_bias"] / trend_den)

        w = self.baseline_weight.value
        dataframe["baseline_raw"] = (1.0 - w) * dataframe["bb_middle"] + w * dataframe["ema_fast"]
        dataframe["dynamic_baseline"] = dataframe["baseline_raw"] + (
            dataframe["trend_score"] * dataframe["atr"] * self.baseline_shift_atr_mult.value
        )

        grid_step = dataframe["atr"] * self.grid_atr_mult.value
        grid_min = dataframe["close"] * 0.002
        grid_max = dataframe["close"] * 0.02
        dataframe["dynamic_grid_step"] = np.clip(grid_step, grid_min, grid_max)

        dataframe["grid_lower_1"] = dataframe["dynamic_baseline"] - dataframe["dynamic_grid_step"] * self.grid_entry_level.value
        dataframe["grid_upper_1"] = dataframe["dynamic_baseline"] + dataframe["dynamic_grid_step"] * self.grid_entry_level.value
        dataframe["grid_breakout_up"] = dataframe["dynamic_baseline"] + dataframe["dynamic_grid_step"] * self.breakout_grid_level.value
        dataframe["grid_breakout_down"] = dataframe["dynamic_baseline"] - dataframe["dynamic_grid_step"] * self.breakout_grid_level.value

        dataframe["zscore"] = (
            (dataframe["close"] - dataframe["dynamic_baseline"]) / dataframe["dynamic_grid_step"].replace(0, np.nan)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        vol_ok = dataframe["volume_ratio"] >= self.volume_ratio_threshold.value
        vol_strong = dataframe["volume_ratio"] >= max(self.volume_ratio_threshold.value + 0.15, 1.05)
        trend_up = dataframe["trend_bias"] > self.trend_bias_threshold.value
        trend_down = dataframe["trend_bias"] < -self.trend_bias_threshold.value

        long_grid_revert = (
            (dataframe["close"] <= dataframe["grid_lower_1"]) &
            (dataframe["rsi"] <= self.rsi_oversold.value) &
            (dataframe["adx"] <= 24) &
            (~trend_down)
        )
        long_trend_pullback = (
            trend_up &
            (dataframe["adx"] <= 30) &
            (dataframe["close"] <= (dataframe["dynamic_baseline"] - dataframe["dynamic_grid_step"] * 0.45)) &
            (dataframe["rsi"] <= self.rsi_overbought.value - 6)
        )
        long_breakout = (
            (dataframe["trend_bias"] > self.trend_bias_threshold.value * 1.15) &
            (dataframe["adx"] >= 20) &
            (dataframe["close"] >= dataframe["grid_breakout_up"]) &
            (dataframe["rsi"] >= 52) &
            vol_strong
        )

        long_condition = (long_grid_revert | long_trend_pullback | long_breakout) & vol_ok
        dataframe.loc[long_condition, "enter_long"] = 1

        short_grid_revert = (
            (dataframe["close"] >= dataframe["grid_upper_1"]) &
            (dataframe["rsi"] >= self.rsi_overbought.value) &
            (dataframe["adx"] <= 24) &
            (~trend_up)
        )
        short_trend_pullback = (
            trend_down &
            (dataframe["adx"] <= 30) &
            (dataframe["close"] >= (dataframe["dynamic_baseline"] + dataframe["dynamic_grid_step"] * 0.45)) &
            (dataframe["rsi"] >= self.rsi_oversold.value + 6)
        )
        short_breakout = (
            (dataframe["trend_bias"] < -self.trend_bias_threshold.value * 1.15) &
            (dataframe["adx"] >= 20) &
            (dataframe["close"] <= dataframe["grid_breakout_down"]) &
            (dataframe["rsi"] <= 48) &
            vol_strong
        )

        short_condition = (short_grid_revert | short_trend_pullback | short_breakout) & vol_ok
        dataframe.loc[short_condition, "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        trend_up = dataframe["trend_bias"] > self.trend_bias_threshold.value
        trend_down = dataframe["trend_bias"] < -self.trend_bias_threshold.value

        long_tp_line = dataframe["dynamic_baseline"] + dataframe["dynamic_grid_step"] * self.grid_exit_level.value
        long_exit = (
            (dataframe["close"] >= long_tp_line) |
            ((dataframe["rsi"] >= self.rsi_overbought.value - 8) & (dataframe["close"] > dataframe["dynamic_baseline"])) |
            trend_down
        )
        dataframe.loc[long_exit, "exit_long"] = 1

        short_tp_line = dataframe["dynamic_baseline"] - dataframe["dynamic_grid_step"] * self.grid_exit_level.value
        short_exit = (
            (dataframe["close"] <= short_tp_line) |
            ((dataframe["rsi"] <= self.rsi_oversold.value + 8) & (dataframe["close"] < dataframe["dynamic_baseline"])) |
            trend_up
        )
        dataframe.loc[short_exit, "exit_short"] = 1

        return dataframe
