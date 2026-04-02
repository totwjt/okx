"""
多空切换策略 V2 - 支持因子配置的参数化策略 V2.0 - Auto-generated strategy
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


class MultiLsV2Strategy(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = True
    timeframe = "15m"
    
    stoploss = -0.251
    minimal_roi = {"0": 0.253, "73": 0.118, "217": 0.043, "298": 0}
    
    trailing_stop = True
    trailing_stop_positive = 0.147
    trailing_stop_positive_offset = 0.149
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    ma_period = IntParameter(100, 300, default=276, space="buy")
    rsi_period = IntParameter(7, 21, default=15, space="buy")
    rsi_oversold = DecimalParameter(20, 35, default=26.6, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(65, 80, default=78.6, decimals=1, space="sell")
    
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
                'max_allowed_drawdown': 0.2}]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ma'] = ta.SMA(dataframe['close'], timeperiod=self.ma_period.value)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)
        dataframe['ma_slope'] = dataframe['ma'].diff(3)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        long_condition = (dataframe['close'] > dataframe['ma']) & (dataframe['ma_slope'] > 0) & (dataframe['rsi'] < rsi_oversold) 
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = (dataframe['close'] < dataframe['ma']) & (dataframe['ma_slope'] < 0) & (dataframe['rsi'] > rsi_overbought) 
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        exit_long_condition = (dataframe['rsi'] > rsi_overbought) | (dataframe['close'] < dataframe['ma']) 
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = (dataframe['rsi'] < rsi_oversold) | (dataframe['close'] > dataframe['ma']) 
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
