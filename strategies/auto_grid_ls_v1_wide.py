"""
网格均值回归策略 V1 宽松变体 - 更宽松的入场条件，更大止盈，适用于高波动或趋势型标的 V1.0 - Auto-generated strategy
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


class GridLsV1WideStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = True
    timeframe = "15m"

    stoploss = -0.15
    minimal_roi = {"0": 0.05, "180": 0.015, "480": 0.0}

    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.035

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    ma_period = IntParameter(24, 96, default=48, space="buy")
    rsi_period = IntParameter(6, 20, default=10, space="buy")
    rsi_oversold = DecimalParameter(25, 50, default=38, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(50, 75, default=62, decimals=1, space="sell")
    bb_period = IntParameter(10, 50, default=36, space="buy")
    bb_std = DecimalParameter(1.5, 2.8, default=2.0, decimals=1, space="buy")
    volume_ma_period = IntParameter(10, 30, default=18, space="buy")
    volume_ratio_threshold = DecimalParameter(1.0, 2.5, default=0.7, decimals=1, space="buy")
    macd_fast = IntParameter(5, 15, default=12, space="buy")
    macd_slow = IntParameter(15, 35, default=26, space="buy")
    macd_signal = IntParameter(5, 15, default=9, space="buy")

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
        return [       {'method': 'CooldownPeriod', 'stop_duration_candles': 6},
        {       'method': 'StoplossGuard',
                'lookback_period_candles': 96,
                'trade_limit': 5,
                'stop_duration_candles': 6,
                'only_per_pair': False},
        {       'method': 'MaxDrawdown',
                'lookback_period_candles': 96,
                'trade_limit': 20,
                'stop_duration_candles': 6,
                'max_allowed_drawdown': 0.25}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ma'] = ta.EMA(dataframe['close'], timeperiod=self.ma_period.value)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)
        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=21)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=89)
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'].replace(0, np.nan)
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle'].replace(0, np.nan)
        dataframe['zscore'] = (dataframe['close'] - dataframe['bb_middle']) / (dataframe['bb_upper'] - dataframe['bb_lower']).replace(0, np.nan)
        dataframe['mean_revert_score'] = ((dataframe['bb_middle'] - dataframe['close']) / dataframe['close'].replace(0, np.nan)) * 100
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70

        long_condition = (  (   (dataframe['adx'] <= 28) &   (dataframe['close'] <= dataframe['bb_lower'] * 1.005) &   (dataframe['rsi'] <= rsi_oversold)  ) |  (   (dataframe['ema_fast'] > dataframe['ema_slow']) &   (dataframe['zscore'] <= -0.6) &   (dataframe['atr_pct'] <= 0.045)  ) ) & (dataframe['volume_ratio'] >= self.volume_ratio_threshold.value) 
        dataframe.loc[long_condition, 'enter_long'] = 1

        short_condition = (  (   (dataframe['adx'] <= 28) &   (dataframe['close'] >= dataframe['bb_upper'] * 0.995) &   (dataframe['rsi'] >= rsi_overbought)  ) |  (   (dataframe['ema_fast'] < dataframe['ema_slow']) &   (dataframe['zscore'] >= 0.6) &   (dataframe['atr_pct'] <= 0.045)  ) ) & (dataframe['volume_ratio'] >= self.volume_ratio_threshold.value) 
        dataframe.loc[short_condition, 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70

        exit_long_condition = (  (dataframe['close'] >= dataframe['bb_middle']) |  ((dataframe['rsi'] >= 50) & (dataframe['zscore'] >= -0.3)) |  (dataframe['atr_pct'] >= 0.06) ) 
        dataframe.loc[exit_long_condition, 'exit_long'] = 1

        exit_short_condition = (  (dataframe['close'] <= dataframe['bb_middle']) |  ((dataframe['rsi'] <= 50) & (dataframe['zscore'] <= 0.3)) |  (dataframe['atr_pct'] >= 0.06) ) 
        dataframe.loc[exit_short_condition, 'exit_short'] = 1

        return dataframe
