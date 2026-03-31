"""
策略1: EMA+RSI 动量剥头皮策略
"""


import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class EMARSIMomentumScalpingV1(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    minimal_roi = {
        "0": 0.025,
        "5": 0.015,
    }

    stoploss = -0.008
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.02

    timeframe = "1m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    ema_fast = IntParameter(5, 15, default=9, space="buy")
    ema_slow = IntParameter(15, 30, default=21, space="buy")
    rsi_period = IntParameter(7, 21, default=14, space="buy")
    rsi_entry_threshold = IntParameter(72, 82, default=78, space="buy")
    volume_ma_window = IntParameter(5, 30, default=20, space="buy")
    volume_multiplier = DecimalParameter(3.5, 5.5, default=4.0, decimals=2, space="buy")

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
            "ema9": {"color": "green"},
            "ema21": {"color": "red"},
        },
        "subplots": {
            "RSI": {"rsi": {"color": "purple"}},
            "Volume": {
                "volume": {"color": "gray"},
                "volume_ma": {"color": "orange"},
            },
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for ema_len in [self.ema_fast.value, self.ema_slow.value]:
            dataframe[f"ema{ema_len}"] = ta.EMA(dataframe["close"], timeperiod=ema_len)

        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=self.rsi_period.value)
        dataframe["volume_ma"] = dataframe["volume"].rolling(window=self.volume_ma_window.value).mean()
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_ma"]
        dataframe["price_change"] = dataframe["close"].pct_change()
        dataframe["sma20"] = ta.SMA(dataframe["close"], timeperiod=20)
        dataframe["sma50"] = ta.SMA(dataframe["close"], timeperiod=50)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_fast = self.ema_fast.value
        ema_slow = self.ema_slow.value
        rsi_threshold = self.rsi_entry_threshold.value
        vol_mult = self.volume_multiplier.value

        ema_cross_up = (
            (dataframe[f"ema{ema_fast}"] > dataframe[f"ema{ema_slow}"]) &
            (dataframe[f"ema{ema_fast}"].shift(1) <= dataframe[f"ema{ema_slow}"].shift(1))
        )

        price_above_ema = (dataframe["close"] > dataframe[f"ema{ema_fast}"]) & (dataframe["close"] > dataframe[f"ema{ema_slow}"])

        rsi_buy = (dataframe["rsi"] > rsi_threshold) & (dataframe["rsi"] > dataframe["rsi"].shift(1))

        volume_confirm = dataframe["volume_ratio"] > vol_mult

        dataframe.loc[
            (ema_cross_up & price_above_ema & rsi_buy & volume_confirm),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_fast = self.ema_fast.value
        ema_slow = self.ema_slow.value

        ema_cross_down = (
            (dataframe[f"ema{ema_fast}"] < dataframe[f"ema{ema_slow}"]) &
            (dataframe[f"ema{ema_fast}"].shift(1) >= dataframe[f"ema{ema_slow}"].shift(1))
        )

        price_below_ema = (dataframe["close"] < dataframe[f"ema{ema_fast}"]) & (dataframe["close"] < dataframe[f"ema{ema_slow}"])

        rsi_reverse = (dataframe["rsi"] < dataframe["rsi"].shift(1)) & (dataframe["rsi"].shift(1) > 65)

        dataframe.loc[(ema_cross_down | price_below_ema | rsi_reverse), "exit_long"] = 1

        return dataframe
