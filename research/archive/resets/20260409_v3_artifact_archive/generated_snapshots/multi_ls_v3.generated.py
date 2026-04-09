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

    stoploss = -0.13
    minimal_roi = {"0": 0.224, "54": 0.123, "113": 0.019, "180": 0}

    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    rsi_period = IntParameter(7, 21, default=13, space="buy")
    rsi_oversold = DecimalParameter(18, 40, default=24.0, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(60, 85, default=84.1, decimals=1, space="sell")
    bb_period = IntParameter(10, 50, default=16, space="buy")
    bb_std = DecimalParameter(1.6, 2.8, default=1.7, decimals=1, space="buy")
    volume_ma_period = IntParameter(10, 30, default=12, space="buy")
    volume_ratio_threshold = DecimalParameter(1.0, 2.5, default=2.0, decimals=1, space="buy")

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
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=21)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=55)
        dataframe['ema_trend'] = ta.EMA(dataframe['close'], timeperiod=180)
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'].replace(0, np.nan)
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle'].replace(0, np.nan)
        dataframe['rsi_slope'] = dataframe['rsi'].diff(2)
        dataframe['donchian_high'] = dataframe['high'].rolling(20).max()
        dataframe['donchian_low'] = dataframe['low'].rolling(20).min()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70

        long_condition = (  (   (dataframe['ema_fast'] > dataframe['ema_slow']) &   (dataframe['close'] > dataframe['ema_trend']) &   (dataframe['adx'] >= 24) &   (dataframe['bb_width'] >= 0.028) &   (dataframe['close'] > dataframe['donchian_high'].shift(1))  ) |  (   (dataframe['adx'] <= 16) &   (dataframe['bb_width'] <= 0.022) &   (dataframe['close'] <= dataframe['bb_lower'] * 1.002) &   (dataframe['rsi'] <= 30) &   (dataframe['rsi_slope'] > 0)  ) ) & (dataframe['atr_pct'] < 0.032) 
        dataframe.loc[long_condition, 'enter_long'] = 1

        short_condition = (  (   (dataframe['ema_fast'] < dataframe['ema_slow']) &   (dataframe['close'] < dataframe['ema_trend']) &   (dataframe['adx'] >= 24) &   (dataframe['bb_width'] >= 0.028) &   (dataframe['close'] < dataframe['donchian_low'].shift(1))  ) |  (   (dataframe['adx'] <= 16) &   (dataframe['bb_width'] <= 0.022) &   (dataframe['close'] >= dataframe['bb_upper'] * 0.998) &   (dataframe['rsi'] >= 70) &   (dataframe['rsi_slope'] < 0)  ) ) & (dataframe['atr_pct'] < 0.032) 
        dataframe.loc[short_condition, 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70

        exit_long_condition = (  ((dataframe['ema_fast'] > dataframe['ema_slow']) & (dataframe['close'] < dataframe['ema_fast'])) |  ((dataframe['adx'] <= 16) & (dataframe['close'] >= dataframe['bb_middle'])) |  (dataframe['atr_pct'] >= 0.032) ) 
        dataframe.loc[exit_long_condition, 'exit_long'] = 1

        exit_short_condition = (  ((dataframe['ema_fast'] < dataframe['ema_slow']) & (dataframe['close'] > dataframe['ema_fast'])) |  ((dataframe['adx'] <= 16) & (dataframe['close'] <= dataframe['bb_middle'])) |  (dataframe['atr_pct'] >= 0.032) ) 
        dataframe.loc[exit_short_condition, 'exit_short'] = 1

        return dataframe
