from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy, merge_informative_pair
from funding_rate_utils import merge_external_funding_rate


class BTCRegimePullbackStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = True
    timeframe = "15m"

    minimal_roi = {
        "0": 0.08,
        "96": 0.03,
        "240": 0.0,
    }
    stoploss = -0.08

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_adx_1h = IntParameter(18, 38, default=24, space="buy")
    buy_bb_window = IntParameter(18, 34, default=24, space="buy")
    buy_bb_std = DecimalParameter(1.6, 2.8, default=2.1, decimals=1, space="buy")
    buy_rsi_long = IntParameter(18, 40, default=30, space="buy")
    buy_rsi_short = IntParameter(60, 82, default=70, space="buy")
    buy_atr_cap = DecimalParameter(0.004, 0.03, default=0.016, decimals=3, space="buy")
    buy_long_funding_max = DecimalParameter(-0.0030, 0.0030, default=0.0008, decimals=4, space="buy")
    buy_short_funding_min = DecimalParameter(-0.0030, 0.0030, default=-0.0008, decimals=4, space="buy")

    sell_exit_rsi_long = IntParameter(52, 76, default=62, space="sell")
    sell_exit_rsi_short = IntParameter(24, 48, default=38, space="sell")
    sell_reclaim_buffer = DecimalParameter(0.001, 0.015, default=0.004, decimals=3, space="sell")

    startup_candle_count = 400

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
                "trade_limit": 3,
                "stop_duration_candles": 16,
                "only_per_pair": True,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 20,
                "stop_duration_candles": 16,
                "max_allowed_drawdown": 0.18,
            },
        ]

    def informative_1h_indicators(self, dataframe: DataFrame) -> DataFrame:
        informative = dataframe.copy()
        informative["ema_fast"] = ta.EMA(informative, timeperiod=55)
        informative["ema_slow"] = ta.EMA(informative, timeperiod=144)
        informative["adx"] = ta.ADX(informative, timeperiod=14)
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb_window = int(self.buy_bb_window.value)
        bb_std = float(self.buy_bb_std.value)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=55)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]

        dataframe["bb_mid"] = dataframe["close"].rolling(bb_window).mean()
        bb_dev = dataframe["close"].rolling(bb_window).std(ddof=0)
        dataframe["bb_upper"] = dataframe["bb_mid"] + bb_dev * bb_std
        dataframe["bb_lower"] = dataframe["bb_mid"] - bb_dev * bb_std

        if self.dp:
            informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="1h")
            informative = self.informative_1h_indicators(informative)
            dataframe = merge_informative_pair(
                dataframe,
                informative[["date", "ema_fast", "ema_slow", "adx"]],
                self.timeframe,
                "1h",
                ffill=True,
            )

        return merge_external_funding_rate(dataframe, metadata["pair"])

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        uptrend = (
            (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
            & (dataframe["adx_1h"] > self.buy_adx_1h.value)
        )
        downtrend = (
            (dataframe["ema_fast_1h"] < dataframe["ema_slow_1h"])
            & (dataframe["adx_1h"] > self.buy_adx_1h.value)
        )

        long_condition = (
            uptrend
            & (dataframe["close"] < dataframe["bb_lower"])
            & (dataframe["rsi"] < self.buy_rsi_long.value)
            & (dataframe["atr_pct"] < self.buy_atr_cap.value)
            & (dataframe["ext_funding_rate"] <= self.buy_long_funding_max.value)
            & (dataframe["volume"] > 0)
        )
        short_condition = (
            downtrend
            & (dataframe["close"] > dataframe["bb_upper"])
            & (dataframe["rsi"] > self.buy_rsi_short.value)
            & (dataframe["atr_pct"] < self.buy_atr_cap.value)
            & (dataframe["ext_funding_rate"] >= self.buy_short_funding_min.value)
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[short_condition, "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        reclaim = self.sell_reclaim_buffer.value

        exit_long = (
            (dataframe["close"] >= dataframe["bb_mid"] * (1 + reclaim))
            | (dataframe["rsi"] > self.sell_exit_rsi_long.value)
            | (dataframe["ema_fast_1h"] < dataframe["ema_slow_1h"])
        )
        exit_short = (
            (dataframe["close"] <= dataframe["bb_mid"] * (1 - reclaim))
            | (dataframe["rsi"] < self.sell_exit_rsi_short.value)
            | (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
        )

        dataframe.loc[exit_long, "exit_long"] = 1
        dataframe.loc[exit_short, "exit_short"] = 1
        return dataframe
