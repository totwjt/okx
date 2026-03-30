"""
VectorBT 回测脚本 - OKX 数据 + 最大回撤分析
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import vectorbt as vbt
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class OKXDataFetcher:
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    OKX_USE_SANDBOX = os.getenv("OKX_USE_SANDBOX", "true").lower() == "true"

    BASE_URL = "https://wspap.okx.com:8443/ws/v5/public" if OKX_USE_SANDBOX else "https://www.okx.com"
    HISTORY_CANDLES_URL = "/api/v5/market/history-candles"

    @classmethod
    def fetch_candles(
        cls,
        symbol: str,
        timeframe: str = "1m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        timeframe_map = {
            "1s": "1s",
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
        }
        tf = timeframe_map.get(timeframe, "1m")

        if start_time is None:
            start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)

        params = {
            "instId": symbol,
            "bar": tf,
            "from": str(start_time // 1000),
            "to": str(end_time // 1000),
            "limit": str(limit),
        }

        try:
            import requests
            url = f"{cls.BASE_URL}{cls.HISTORY_CANDLES_URL}"
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if data.get("code") != "0":
                print(f"API Error: {data.get('msg')}")
                return pd.DataFrame()

            candles = data.get("data", [])
            if not candles:
                return pd.DataFrame()

            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "vol", "volCcy", "confirm", "timestamp2"])
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df = df.set_index("timestamp")
            df = df[["open", "high", "low", "close", "vol"]].astype(float)
            df.columns = ["open", "high", "low", "close", "volume"]

            return df
        except Exception as e:
            print(f"获取数据失败: {e}")
            return pd.DataFrame()


class VolumeRatioStrategyBacktest:
    BUY_THRESHOLD = 0.7
    SELL_THRESHOLD = 1.5
    VOLUME_MA_WINDOW = 20
    STOPLOSS = 0.03
    TAKEPROFIT = 0.02

    @classmethod
    def run(
        cls,
        symbol: str = "BTC-USDT",
        timeframe: str = "5m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_cash: float = 10000,
    ) -> dict:
        if start_date:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        else:
            start_ts = None
        if end_date:
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
        else:
            end_ts = None

        df = OKXDataFetcher.fetch_candles(symbol, timeframe, start_ts, end_ts)
        if df.empty:
            return {"error": "No data fetched"}

        df["volume_ma"] = df["volume"].rolling(window=cls.VOLUME_MA_WINDOW).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"]
        df["price_change"] = df["close"].pct_change()

        entries = (
            (df["volume_ratio"] < cls.BUY_THRESHOLD)
            & (df["price_change"] < 0)
            & (df["volume"] > 0)
        )
        exits = (
            (df["volume_ratio"] > cls.SELL_THRESHOLD)
            & (df["price_change"] > 0)
            & (df["volume"] > 0)
        )

        pf = vbt.Portfolio.from_signals(
            df["close"],
            entries=entries,
            exits=exits,
            sl_stop=cls.STOPLOSS,
            tp_stop=cls.TAKEPROFIT,
            init_cash=initial_cash,
            fees=0.001,
            slippage=0.0005,
        )

        stats = pf.stats()
        returns = pf.returns()

        running_max = (1 + returns).cumprod().cummax()
        drawdown = (1 + returns).cumprod() / running_max - 1
        max_drawdown = drawdown.min()

        drawdown_periods = []
        in_drawdown = False
        start_idx = None
        for i, d in enumerate(drawdown):
            if d < -0.01 and not in_drawdown:
                in_drawdown = True
                start_idx = i
            elif d >= 0 and in_drawdown:
                in_drawdown = False
                if start_idx is not None:
                    drawdown_periods.append((start_idx, i))

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": df.index[0].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
            "total_trades": int(stats["total_trades"]),
            "winning_trades": int(stats["winning_trades"]),
            "losing_trades": int(stats["losing_trades"]),
            "win_rate": float(stats["win_rate"]),
            "total_return": float(stats["total_return"]),
            "max_drawdown": float(max_drawdown),
            "avg_trade_return": float(stats["avg_trade_return"]),
            "profit_factor": float(stats.get("profit_factor", 0)),
            "drawdown_periods": len(drawdown_periods),
        }

        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VectorBT 回测")
    parser.add_argument("--symbol", default="BTC-USDT", help="交易对")
    parser.add_argument("--timeframe", default="5m", help="时间框架")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10000, help="初始资金")
    args = parser.parse_args()

    result = VolumeRatioStrategyBacktest.run(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.cash,
    )

    print("\n" + "=" * 50)
    print("回测结果")
    print("=" * 50)
    for k, v in result.items():
        print(f"{k}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    main()
