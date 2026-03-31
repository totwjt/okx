import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class VolumeRatioStrategyV1(IStrategy):
    INTERFACE_VERSION = 3

    can_short = False

    minimal_roi = {
        "0": 0.015,
        "10": 0.01,
    }

    stoploss = -0.015

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_volume_ratio_threshold = DecimalParameter(0.2, 0.4, default=0.3, decimals=2, space="buy")
    sell_volume_ratio_threshold = DecimalParameter(2.0, 3.5, default=2.5, decimals=2, space="sell")
    volume_ma_window = IntParameter(8, 20, default=10, space="buy")

    startup_candle_count = 50

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "volume_ratio": {"color": "blue"},
        },
        "subplots": {
            "Volume": {
                "volume": {"color": "gray"},
                "volume_ma": {"color": "orange"},
            },
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        window = self.volume_ma_window.value
        dataframe["volume_ma"] = dataframe["volume"].rolling(window=window).mean()
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_ma"]

        dataframe["price_change"] = dataframe["close"].pct_change()
        dataframe["ma20"] = ta.SMA(dataframe["close"], timeperiod=20)
        dataframe["ma50"] = ta.SMA(dataframe["close"], timeperiod=50)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        price_in_range = (dataframe["close"] > dataframe["ma50"]) & (dataframe["close"] < dataframe["ma20"])
        
        price_dropping = dataframe["close"] < dataframe["close"].shift(1)
        
        low_volume = dataframe["volume_ratio"] < self.buy_volume_ratio_threshold.value

        dataframe.loc[
            (price_in_range & price_dropping & low_volume),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["volume_ratio"] > self.sell_volume_ratio_threshold.value)
                & (dataframe["close"] < dataframe["close"].shift(1))
            ),
            "exit_long",
        ] = 1

        return dataframe
