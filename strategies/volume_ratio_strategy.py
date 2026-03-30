"""
OKX 超短线量能策略机器人
核心策略：缩量下跌买入，放量上涨卖出
"""
import numpy as np
import pandas as pd
from pandas import DataFrame
from typing import Optional

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class VolumeRatioStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = False

    minimal_roi = {
        "0": 0.02,
        "5": 0.01,
        "30": 0.005,
    }

    stoploss = -0.03

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_volume_ratio_threshold = DecimalParameter(0.3, 0.9, default=0.7, decimals=2, space="buy")
    sell_volume_ratio_threshold = DecimalParameter(1.1, 2.5, default=1.5, decimals=2, space="sell")
    volume_ma_window = IntParameter(5, 50, default=20, space="buy")

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
        dataframe["price_direction"] = np.where(dataframe["close"] > dataframe["close"].shift(1), 1, -1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["volume_ratio"] < self.buy_volume_ratio_threshold.value)
                & (dataframe["price_change"] < 0)
                & (dataframe["volume"] > 0)
                & (dataframe["volume_ratio"].notna())
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["volume_ratio"] > self.sell_volume_ratio_threshold.value)
                & (dataframe["price_change"] > 0)
                & (dataframe["volume"] > 0)
                & (dataframe["volume_ratio"].notna())
            ),
            "exit_long",
        ] = 1

        return dataframe
