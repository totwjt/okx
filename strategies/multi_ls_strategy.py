import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class MultiLSStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = True
    
    stoploss = -0.05
    
    minimal_roi = {
        "0": 0.02,
    }
    
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.025
    
    timeframe = "15m"
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    
    ma_period = IntParameter(100, 300, default=200, space="buy")
    rsi_period = IntParameter(7, 21, default=14, space="buy")
    rsi_oversold = DecimalParameter(20, 35, default=30, decimals=1, space="buy")
    rsi_overbought = DecimalParameter(65, 80, default=70, decimals=1, space="sell")
    
    startup_candle_count = 300
    
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}
    
    plot_config = {
        "main_plot": {
            "ma": {"color": "blue"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "purple"},
            },
        },
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ma_period = self.ma_period.value
        dataframe['ma'] = ta.SMA(dataframe['close'], timeperiod=ma_period)
        dataframe['ma_slope'] = dataframe['ma'].diff(3)
        
        rsi_period = self.rsi_period.value
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=rsi_period)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        rsi_oversold = self.rsi_oversold.value
        rsi_overbought = self.rsi_overbought.value
        
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        long_condition = (
            (dataframe['close'] > dataframe['ma']) &
            (dataframe['ma_slope'] > 0) &
            (dataframe['rsi'] < rsi_oversold)
        )
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = (
            (dataframe['close'] < dataframe['ma']) &
            (dataframe['ma_slope'] < 0) &
            (dataframe['rsi'] > rsi_overbought)
        )
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        rsi_oversold = self.rsi_oversold.value
        rsi_overbought = self.rsi_overbought.value
        
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        exit_long_condition = (
            (dataframe['rsi'] > rsi_overbought) |
            (dataframe['close'] < dataframe['ma'])
        )
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = (
            (dataframe['rsi'] < rsi_oversold) |
            (dataframe['close'] > dataframe['ma'])
        )
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
