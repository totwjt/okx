"""
多空结构化策略 V3（Regime + TrendBreakout + RangeReversal + RiskBudget） V3.0 - Auto-generated strategy
Trading Mode: futures
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


class MultiLsV3Strategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = True
    timeframe = "15m"

    stoploss = -0.11
    minimal_roi = {"0": 0.08, "60": 0.025, "180": 0.0}

    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    rsi_period = IntParameter(7, 21, default=13, space="buy")
    rsi_oversold = DecimalParameter(18, 40, default=31, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(60, 85, default=69, decimals=1, space="sell")
    bb_period = IntParameter(10, 50, default=17, space="buy")
    bb_std = DecimalParameter(1.6, 2.8, default=1.9, decimals=1, space="buy")
    bb_width_trend_min = DecimalParameter(0.015, 0.05, default=0.024, decimals=3, space="buy")
    bb_width_range_max = DecimalParameter(0.01, 0.04, default=0.026, decimals=3, space="buy")
    volume_ma_period = IntParameter(10, 30, default=16, space="buy")
    volume_ratio_threshold = DecimalParameter(0.6, 2.5, default=0.9, decimals=2, space="buy")
    adx_period = IntParameter(7, 28, default=14, space="buy")
    adx_trend_min = DecimalParameter(18, 36, default=22, decimals=1, space="buy")
    adx_range_max = DecimalParameter(8, 24, default=18, decimals=1, space="buy")
    atr_period = IntParameter(7, 28, default=14, space="buy")
    atr_entry_max = DecimalParameter(0.015, 0.06, default=0.035, decimals=3, space="buy")
    atr_exit_max = DecimalParameter(0.02, 0.08, default=0.034, decimals=3, space="sell")
    zscore_period = IntParameter(12, 72, default=28, space="buy")
    zscore_entry_abs = DecimalParameter(0.6, 2.2, default=0.95, decimals=2, space="buy")
    zscore_exit_abs = DecimalParameter(0.1, 1.2, default=0.24, decimals=2, space="sell")
    donchian_period = IntParameter(10, 55, default=18, space="buy")

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
        return [       {'method': 'CooldownPeriod', 'stop_duration_candles': 12},
        {       'method': 'StoplossGuard',
                'lookback_period_candles': 96,
                'trade_limit': 3,
                'stop_duration_candles': 12,
                'only_per_pair': False},
        {       'method': 'MaxDrawdown',
                'lookback_period_candles': 96,
                'trade_limit': 20,
                'stop_duration_candles': 12,
                'max_allowed_drawdown': 0.22}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.adx_period.value)
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.atr_period.value)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'].replace(0, np.nan)
        dataframe['zscore_mean'] = dataframe['close'].rolling(self.zscore_period.value).mean()
        dataframe['zscore_std'] = dataframe['close'].rolling(self.zscore_period.value).std()
        dataframe['zscore'] = (dataframe['close'] - dataframe['zscore_mean']) / dataframe['zscore_std'].replace(0, np.nan)
        dataframe['donchian_high'] = dataframe['high'].rolling(self.donchian_period.value).max()
        dataframe['donchian_low'] = dataframe['low'].rolling(self.donchian_period.value).min()
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=21)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=55)
        dataframe['ema_trend'] = ta.EMA(dataframe['close'], timeperiod=180)
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle'].replace(0, np.nan)
        dataframe['rsi_slope'] = dataframe['rsi'].diff(2)
        dataframe['trend_strength'] = (dataframe['ema_fast'] - dataframe['ema_slow']) / dataframe['close'].replace(0, np.nan)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 31
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 69
        bb_width_trend_min = self.bb_width_trend_min.value if hasattr(self, 'bb_width_trend_min') else 0.024
        bb_width_range_max = self.bb_width_range_max.value if hasattr(self, 'bb_width_range_max') else 0.026
        volume_ratio_threshold = self.volume_ratio_threshold.value if hasattr(self, 'volume_ratio_threshold') else 0.9
        adx_trend_min = self.adx_trend_min.value if hasattr(self, 'adx_trend_min') else 22
        adx_range_max = self.adx_range_max.value if hasattr(self, 'adx_range_max') else 18
        atr_entry_max = self.atr_entry_max.value if hasattr(self, 'atr_entry_max') else 0.035
        zscore_entry_abs = self.zscore_entry_abs.value if hasattr(self, 'zscore_entry_abs') else 0.95

        long_condition = (  (   (dataframe['ema_fast'] > dataframe['ema_slow']) &   (dataframe['close'] > dataframe['ema_trend']) &   (dataframe['adx'] >= adx_trend_min) &   (dataframe['bb_width'] >= bb_width_trend_min) &   (dataframe['close'] > dataframe['donchian_high'].shift(1))  ) |  (   (dataframe['adx'] <= adx_range_max) &   (dataframe['bb_width'] <= bb_width_range_max) &   (dataframe['close'] <= dataframe['bb_lower']) &   (dataframe['zscore'] <= -zscore_entry_abs) &   (dataframe['rsi'] <= rsi_oversold)  ) |  (   (dataframe['rsi'] <= rsi_oversold - 3) &   (dataframe['zscore'] <= -zscore_entry_abs * 1.20) &   (dataframe['rsi_slope'] > 0)  ) ) & (dataframe['atr_pct'] <= atr_entry_max) & (dataframe['volume_ratio'] >= volume_ratio_threshold) 
        dataframe.loc[long_condition, 'enter_long'] = 1

        short_condition = (  (   (dataframe['ema_fast'] < dataframe['ema_slow']) &   (dataframe['close'] < dataframe['ema_trend']) &   (dataframe['adx'] >= adx_trend_min) &   (dataframe['bb_width'] >= bb_width_trend_min) &   (dataframe['close'] < dataframe['donchian_low'].shift(1))  ) |  (   (dataframe['adx'] <= adx_range_max) &   (dataframe['bb_width'] <= bb_width_range_max) &   (dataframe['close'] >= dataframe['bb_upper']) &   (dataframe['zscore'] >= zscore_entry_abs) &   (dataframe['rsi'] >= rsi_overbought)  ) |  (   (dataframe['rsi'] >= rsi_overbought + 3) &   (dataframe['zscore'] >= zscore_entry_abs * 1.20) &   (dataframe['rsi_slope'] < 0)  ) ) & (dataframe['atr_pct'] <= atr_entry_max) & (dataframe['volume_ratio'] >= volume_ratio_threshold) 
        dataframe.loc[short_condition, 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 31
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 69
        bb_width_trend_min = self.bb_width_trend_min.value if hasattr(self, 'bb_width_trend_min') else 0.024
        bb_width_range_max = self.bb_width_range_max.value if hasattr(self, 'bb_width_range_max') else 0.026
        volume_ratio_threshold = self.volume_ratio_threshold.value if hasattr(self, 'volume_ratio_threshold') else 0.9
        adx_trend_min = self.adx_trend_min.value if hasattr(self, 'adx_trend_min') else 22
        adx_range_max = self.adx_range_max.value if hasattr(self, 'adx_range_max') else 18
        atr_exit_max = self.atr_exit_max.value if hasattr(self, 'atr_exit_max') else 0.034
        zscore_exit_abs = self.zscore_exit_abs.value if hasattr(self, 'zscore_exit_abs') else 0.24

        exit_long_condition = (  ((dataframe['ema_fast'] > dataframe['ema_slow']) & (dataframe['close'] < dataframe['ema_fast'])) |  ((dataframe['adx'] <= adx_range_max) & (dataframe['close'] >= dataframe['bb_middle'])) |  (dataframe['zscore'] >= -zscore_exit_abs) |  (dataframe['atr_pct'] >= atr_exit_max) ) 
        dataframe.loc[exit_long_condition, 'exit_long'] = 1

        exit_short_condition = (  ((dataframe['ema_fast'] < dataframe['ema_slow']) & (dataframe['close'] > dataframe['ema_fast'])) |  ((dataframe['adx'] <= adx_range_max) & (dataframe['close'] <= dataframe['bb_middle'])) |  (dataframe['zscore'] <= zscore_exit_abs) |  (dataframe['atr_pct'] >= atr_exit_max) ) 
        dataframe.loc[exit_short_condition, 'exit_short'] = 1

        return dataframe
