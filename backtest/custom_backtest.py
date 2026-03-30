"""
自定义回测脚本 - 纯 pandas 实现，兼容 Python 3.14
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from okx import MarketData

load_dotenv()

API_KEY = os.getenv("OKX_API_KEY", "")
SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
USE_SANDBOX = os.getenv("OKX_USE_SANDBOX", "true").lower() == "true"

OKX_FEE = 0.0005
SLIPPAGE = 0.0002


def fetch_candles(symbol: str, timeframe: str, limit: int = 2000) -> Optional[list]:
    flag = "0" if USE_SANDBOX else "1"
    market = MarketData.MarketAPI(API_KEY, SECRET_KEY, PASSPHRASE, flag=flag)
    
    tf_map = {"1s": "1s", "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
    bar = tf_map.get(timeframe, "1m")
    
    all_candles = []
    max_pages = (limit // 300) + 1
    
    for page in range(max_pages):
        if page == 0:
            result = market.get_history_candlesticks(instId=symbol, bar=bar, limit=300)
        else:
            after = all_candles[-1][0]
            result = market.get_history_candlesticks(instId=symbol, bar=bar, limit=300, after=after)
        
        if result.get("code") != "0":
            print(f"API Error: {result.get('msg')}")
            break
        
        data = result.get("data", [])
        if not data:
            break
        
        all_candles.extend(data)
        
        if len(all_candles) >= limit:
            break
    
    return all_candles[:limit] if all_candles else None


def calculate_indicators(candles: list, volume_ma_window: int = 20):
    import pandas as pd
    
    df = pd.DataFrame(candles, columns=["ts", "open", "high", "low", "close", "vol", "volCcy", "confirm", "ts2"])
    df["timestamp"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
    df = df.set_index("timestamp")
    df = df[["open", "high", "low", "close", "vol"]].astype(float)
    df.columns = ["open", "high", "low", "close", "volume"]
    
    df = df.sort_index()
    
    df["volume_ma"] = df["volume"].rolling(window=volume_ma_window).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"]
    df["price_change"] = df["close"].pct_change()
    
    return df


def run_backtest(
    candles: list,
    buy_threshold: float = 0.7,
    sell_threshold: float = 1.5,
    volume_ma_window: int = 20,
    initial_cash: float = 10000,
    stoploss: float = 0.03,
    takeprofit: float = 0.02,
):
    import pandas as pd
    import numpy as np
    
    df = calculate_indicators(candles, volume_ma_window)
    df = df.dropna()
    
    cash = initial_cash
    position = 0
    entry_price = 0
    trades = []
    equity_curve = [initial_cash]
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        price = row["close"]
        volume_ratio = row["volume_ratio"]
        price_change = row["price_change"]
        
        if pd.isna(volume_ratio):
            equity_curve.append(cash + position * price if position > 0 else cash)
            continue
        
        if position == 0:
            if volume_ratio < buy_threshold and price_change < 0:
                buy_price = price * (1 + SLIPPAGE)
                if buy_price > 0:
                    position = cash / buy_price
                    entry_price = buy_price
                    cash -= position * buy_price
                    trades.append({
                        "type": "BUY",
                        "price": buy_price,
                        "shares": position,
                        "time": row.name,
                    })
        else:
            pnl_pct = (price - entry_price) / entry_price
            should_exit = False
            exit_reason = ""
            
            if pnl_pct <= -stoploss:
                should_exit = True
                exit_reason = "SL"
            elif pnl_pct >= takeprofit:
                should_exit = True
                exit_reason = "TP"
            elif volume_ratio > sell_threshold and price_change > 0:
                should_exit = True
                exit_reason = "SIGNAL"
            
            if should_exit:
                sell_price = price * (1 - SLIPPAGE)
                cash += position * sell_price
                trades.append({
                    "type": "SELL",
                    "price": sell_price,
                    "shares": position,
                    "time": row.name,
                    "pnl_pct": pnl_pct,
                    "reason": exit_reason,
                })
                position = 0
                entry_price = 0
        
        current_equity = cash + position * price if position > 0 else cash
        equity_curve.append(current_equity)
    
    final_equity = cash + position * df.iloc[-1]["close"] if position > 0 else cash
    
    winning_trades = [t for t in trades if t.get("type") == "SELL" and t.get("pnl_pct", 0) > 0]
    losing_trades = [t for t in trades if t.get("type") == "SELL" and t.get("pnl_pct", 0) <= 0]
    
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    
    total_wins = sum([t["pnl_pct"] for t in winning_trades]) if winning_trades else 0
    total_losses = abs(sum([t["pnl_pct"] for t in losing_trades])) if losing_trades else 0.0001
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    total_return = (final_equity - initial_cash) / initial_cash * 100
    
    return {
        "symbol": df.iloc[0].name,
        "start_date": df.index[0].strftime("%Y-%m-%d"),
        "end_date": df.index[-1].strftime("%Y-%m-%d"),
        "initial_cash": initial_cash,
        "final_equity": final_equity,
        "total_return": total_return,
        "total_trades": len(trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "trades": trades,
    }


def print_report(result: dict):
    print("\n" + "=" * 60)
    print("回 测 报 告")
    print("=" * 60)
    print(f"交易对: {result.get('symbol')}")
    print(f"时间范围: {result.get('start_date')} ~ {result.get('end_date')}")
    print("-" * 60)
    print(f"初始资金: ${result['initial_cash']:,.2f}")
    print(f"最终权益: ${result['final_equity']:,.2f}")
    print(f"总收益率: {result['total_return']:.2f}%")
    print("-" * 60)
    print(f"总交易次数: {result['total_trades']}")
    print(f"盈利交易: {result['winning_trades']}")
    print(f"亏损交易: {result['losing_trades']}")
    print(f"胜率: {result['win_rate']:.2f}%")
    print(f"盈亏比: {result['profit_factor']:.2f}")
    print("-" * 60)
    print(f"最大回撤: {result['max_drawdown']:.2f}%")
    print("=" * 60)
    
    print("\n最近 10 笔交易:")
    for t in result["trades"][-10:]:
        if t["type"] == "BUY":
            print(f"  {t['time'].strftime('%Y-%m-%d %H:%M')} 买入 @ ${t['price']:.2f}")
        else:
            pnl = t.get("pnl_pct", 0) * 100
            print(f"  {t['time'].strftime('%Y-%m-%d %H:%M')} 卖出 @ ${t['price']:.2f} ({pnl:+.2f}%) [{t.get('reason', '')}]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--buy-threshold", type=float, default=0.7)
    parser.add_argument("--sell-threshold", type=float, default=1.5)
    parser.add_argument("--volume-window", type=int, default=20)
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()
    
    print(f"获取 {args.symbol} {args.timeframe} 数据...")
    candles = fetch_candles(args.symbol, args.timeframe, args.limit)
    
    if not candles:
        print("获取数据失败")
        sys.exit(1)
    
    print(f"获取到 {len(candles)} 根K线")
    
    result = run_backtest(
        candles,
        buy_threshold=args.buy_threshold,
        sell_threshold=args.sell_threshold,
        volume_ma_window=args.volume_window,
    )
    
    print_report(result)
