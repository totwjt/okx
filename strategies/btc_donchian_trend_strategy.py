from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy, merge_informative_pair


class BTCDonchianTrendStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = True
    timeframe = "15m"

    minimal_roi = {
        "0": 0.12,
        "72": 0.05,
        "180": 0.02,
        "360": 0.0,
    }
    stoploss = -0.09

    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_adx_1h = IntParameter(16, 38, default=24, space="buy")
    buy_breakout_window = IntParameter(20, 72, default=36, space="buy")
    buy_rsi_long = IntParameter(48, 72, default=58, space="buy")
    buy_rsi_short = IntParameter(28, 52, default=42, space="buy")
    buy_atr_floor = DecimalParameter(0.002, 0.025, default=0.008, decimals=3, space="buy")

    sell_exit_ema = IntParameter(10, 55, default=21, space="sell")
    sell_exit_rsi_long = IntParameter(35, 58, default=46, space="sell")
    sell_exit_rsi_short = IntParameter(42, 68, default=54, space="sell")

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
            {"method": "CooldownPeriod", "stop_duration_candles": 6},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 96,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": True,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 20,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.16,
            },
        ]

    def informative_1h_indicators(self, dataframe: DataFrame) -> DataFrame:
        informative = dataframe.copy()
        informative["ema_fast"] = ta.EMA(informative, timeperiod=34)
        informative["ema_slow"] = ta.EMA(informative, timeperiod=89)
        informative["adx"] = ta.ADX(informative, timeperiod=14)
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        breakout_window = int(self.buy_breakout_window.value)
        exit_ema = int(self.sell_exit_ema.value)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["exit_ema"] = ta.EMA(dataframe, timeperiod=exit_ema)

        dataframe["donchian_high"] = dataframe["high"].rolling(breakout_window).max().shift(1)
        dataframe["donchian_low"] = dataframe["low"].rolling(breakout_window).min().shift(1)

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

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        trend_up = (
            (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
            & (dataframe["adx_1h"] > self.buy_adx_1h.value)
        )
        trend_down = (
            (dataframe["ema_fast_1h"] < dataframe["ema_slow_1h"])
            & (dataframe["adx_1h"] > self.buy_adx_1h.value)
        )

        long_condition = (
            trend_up
            & (dataframe["close"] > dataframe["donchian_high"])
            & (dataframe["rsi"] > self.buy_rsi_long.value)
            & (dataframe["atr_pct"] > self.buy_atr_floor.value)
            & (dataframe["volume"] > 0)
        )
        short_condition = (
            trend_down
            & (dataframe["close"] < dataframe["donchian_low"])
            & (dataframe["rsi"] < self.buy_rsi_short.value)
            & (dataframe["atr_pct"] > self.buy_atr_floor.value)
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[short_condition, "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        exit_long = (
            (dataframe["close"] < dataframe["exit_ema"])
            | (dataframe["rsi"] < self.sell_exit_rsi_long.value)
            | (dataframe["ema_fast_1h"] < dataframe["ema_slow_1h"])
        )
        exit_short = (
            (dataframe["close"] > dataframe["exit_ema"])
            | (dataframe["rsi"] > self.sell_exit_rsi_short.value)
            | (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
        )

        dataframe.loc[exit_long, "exit_long"] = 1
        dataframe.loc[exit_short, "exit_short"] = 1
        return dataframe
