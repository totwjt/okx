"""
多空切换策略回测脚本 - VectorBT
基于归档策略规范: research/archive/docs/3多空切换.md
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
from dotenv import load_dotenv
from okx import MarketData

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()


class OKXDataFetcher:
    """OKX 数据获取器"""
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    OKX_USE_SANDBOX = os.getenv("OKX_USE_SANDBOX", "true").lower() == "true"

    @classmethod
    def fetch_candles(
        cls,
        symbol: str,
        timeframe: str = "1m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 3000,
    ) -> pd.DataFrame:
        """获取K线数据"""
        timeframe_map = {
            "1s": "1s", "1m": "1m", "5m": "5m", "15m": "15m",
            "1h": "1H", "4h": "4H", "1d": "1D",
        }
        tf = timeframe_map.get(timeframe, "1m")

        if start_time is None:
            start_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)

        try:
            flag = "0" if cls.OKX_USE_SANDBOX else "1"
            market = MarketData.MarketAPI(cls.OKX_API_KEY, cls.OKX_SECRET_KEY, cls.OKX_PASSPHRASE, flag=flag)
            
            # 分批获取数据以获取更多历史数据
            all_candles = []
            current_start = start_time
            max_retries = 10
            
            while current_start < end_time and len(all_candles) < 30000:
                result = market.get_history_candles(instId=symbol, bar=tf, limit=min(limit, 3000), after=str(int(current_start)))
                
                if result.get("code") != "0":
                    print(f"API Error: {result.get('msg')}")
                    break
                
                candles = result.get("data", [])
                if not candles:
                    break
                    
                all_candles.extend(candles)
                
                # 更新起始时间继续获取
                if candles:
                    current_start = int(candles[-1][0]) + 1
                else:
                    break

            if not all_candles:
                return pd.DataFrame()

            df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "vol", "volCcy", "confirm", "timestamp2"])
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df = df.set_index("timestamp")
            df = df[["open", "high", "low", "close", "vol"]].astype(float)
            df.columns = ["open", "high", "low", "close", "volume"]
            
            # 去重并排序
            df = df[~df.index.duplicated(keep='first')]
            df = df.sort_index()
            
            return df
        except Exception as e:
            print(f"获取数据失败: {e}")
            return pd.DataFrame()


class MultiTrendStrategy:
    """多空切换策略"""
    
    # 默认参数
    DEFAULT_PARAMS = {
        'ma_period_4h': 200,      # 4小时MA周期
        'ma_period_15m': 200,    # 15分钟MA周期
        'rsi_period': 14,        # RSI周期
        'rsi_oversold': 30,      # RSI超卖阈值
        'rsi_overbought': 70,   # RSI超买阈值
        'bb_period': 20,        # 布林带周期
        'bb_std': 2,            # 布林带标准差倍数
        'volume_ma_period': 20, # 成交量MA周期
        'min_trade_interval': 10, # 最小交易间隔(K线数)
        'stoploss': 0.02,       # 止损比例
        'takeprofit': 0.03,     # 止盈比例
        'trade_per_day': 5,     # 每日最大交易次数
    }
    
    @classmethod
    def calculate_indicators(cls, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """计算所有指标"""
        result = df.copy()
        
        ma_period_4h = int(params['ma_period_4h'])
        ma_period_15m = int(params['ma_period_15m'])
        rsi_period = int(params['rsi_period'])
        bb_period = int(params['bb_period'])
        bb_std = float(params['bb_std'])
        volume_ma_period = int(params['volume_ma_period'])
        
        # 4小时K线数据
        df_4h = df.resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        
        # MA指标
        result[f'ma_{ma_period_15m}'] = result['close'].rolling(window=ma_period_15m).mean()
        result['ma_slope'] = result[f'ma_{ma_period_15m}'].pct_change(5)  # MA斜率
        
        # 4小时MA
        if not df_4h.empty:
            result['ma_4h_200'] = df_4h['close'].rolling(window=ma_period_4h).mean()
            result['ma_4h_slope'] = result['ma_4h_200'].pct_change(5)
            # 向前填充4小时数据
            result['ma_4h_200'] = result['ma_4h_200'].ffill()
            result['ma_4h_slope'] = result['ma_4h_slope'].ffill()
        
        # RSI
        delta = result['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        result['bb_middle'] = result['close'].rolling(window=bb_period).mean()
        bb_std_val = result['close'].rolling(window=bb_period).std()
        result['bb_upper'] = result['bb_middle'] + bb_std_val * bb_std
        result['bb_lower'] = result['bb_middle'] - bb_std_val * bb_std
        
        # 成交量MA
        result['volume_ma'] = result['volume'].rolling(window=volume_ma_period).mean()
        
        return result
    
    @classmethod
    def determine_market_state(cls, df: pd.DataFrame) -> pd.Series:
        """判定市场状态"""
        price = df['close']
        ma_4h = df.get('ma_4h_200')
        ma_slope = df.get('ma_4h_slope')
        
        state = pd.Series('range', index=df.index)
        
        if ma_4h is not None and ma_slope is not None:
            # 牛市: 价格在4H MA上方且MA向上
            bull_condition = (price > ma_4h) & (ma_slope > 0)
            # 熊市: 价格在4H MA下方且MA向下
            bear_condition = (price < ma_4h) & (ma_slope < 0)
            
            state = np.where(bull_condition, 'bull', state)
            state = np.where(bear_condition, 'bear', state)
        
        return state
    
    @classmethod
    def generate_signals(cls, df: pd.DataFrame, params: dict) -> tuple:
        """生成交易信号"""
        df = cls.calculate_indicators(df, params)
        market_state = cls.determine_market_state(df)
        
        rsi = df['rsi']
        close = df['close']
        ma_15m = df[f'ma_{int(params["ma_period_15m"])}']
        bb_upper = df['bb_upper']
        bb_lower = df['bb_lower']
        volume_ma = df['volume_ma']
        
        rsi_oversold = float(params['rsi_oversold'])
        rsi_overbought = float(params['rsi_overbought'])
        min_interval = int(params['min_trade_interval'])
        
        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)
        
        # 过滤条件: 成交量充足
        volume_filter = df['volume'] > volume_ma * 0.5
        
        # 牛市(只做多): 价格在15m MA上方，RSI超卖或触及布林下轨
        bull_entry = (market_state == 'bull') & (close > ma_15m) & (
            (rsi < rsi_oversold) | (close < bb_lower)
        ) & volume_filter
        
        # 牛市平仓: RSI超买或触及布林上轨
        bull_exit = (market_state == 'bull') & (
            (rsi > rsi_overbought) | (close > bb_upper)
        )
        
        # 熊市(只做空): 价格在15m MA下方，RSI超买或触及布林上轨
        bear_entry = (market_state == 'bear') & (close < ma_15m) & (
            (rsi > rsi_overbought) | (close > bb_upper)
        ) & volume_filter
        
        # 熊市平仓: RSI超卖或触及布林下轨
        bear_exit = (market_state == 'bear') & (
            (rsi < rsi_oversold) | (close < bb_lower)
        )
        
        entries = bull_entry | bear_entry
        exits = bull_exit | bear_exit
        
        # 应用最小间隔过滤
        last_trade_idx = -min_interval
        for i in range(len(df)):
            if entries.iloc[i]:
                if i - last_trade_idx >= min_interval:
                    last_trade_idx = i
                else:
                    entries.iloc[i] = False
        
        return entries, exits
    
    @classmethod
    def run_backtest(
        cls,
        df: pd.DataFrame,
        params: dict,
        initial_cash: float = 10000,
        fees: float = 0.001,
        slippage: float = 0.0005,
    ) -> dict:
        """运行回测"""
        if df.empty or len(df) < 300:
            return {"error": "数据不足"}
        
        entries, exits = cls.generate_signals(df, params)
        
        # 过滤有效信号
        valid_entries = entries & (df['volume'] > 0)
        valid_exits = exits & (df['volume'] > 0)
        
        if valid_entries.sum() == 0:
            return {"error": "无有效交易信号"}
        
        pf = vbt.Portfolio.from_signals(
            df['close'],
            entries=valid_entries,
            exits=valid_exits,
            sl_stop=float(params['stoploss']),
            tp_stop=float(params['takeprofit']),
            init_cash=initial_cash,
            fees=fees,
            slippage=slippage,
        )
        
        stats = pf.stats()
        returns = pf.returns()
        
        # 计算最大回撤
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = cumulative_returns / running_max - 1
        max_drawdown = drawdown.min()
        
        # 计算夏普比率
        if returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(252 * 24 * 12)  # 5分钟周期年化
        else:
            sharpe = 0
        
        result = {
            'total_trades': int(stats.get('total_trades', 0)),
            'winning_trades': int(stats.get('winning_trades', 0)),
            'losing_trades': int(stats.get('losing_trades', 0)),
            'win_rate': float(stats.get('win_rate', 0)),
            'total_return': float(stats.get('total_return', 0)),
            'max_drawdown': float(max_drawdown),
            'sharpe_ratio': float(sharpe),
            'profit_factor': float(stats.get('profit_factor', 0)),
            'avg_trade_return': float(stats.get('avg_trade_return', 0)),
        }
        
        return result


def optimize_params(
    df: pd.DataFrame,
    param_grid: dict,
    initial_cash: float = 10000,
) -> dict:
    """参数优化"""
    results = []
    param_combinations = list(product(*param_grid.values()))
    param_names = list(param_grid.keys())
    
    total = len(param_combinations)
    print(f"开始参数优化，共 {total} 种组合...")
    
    for idx, params in enumerate(param_combinations):
        param_dict = dict(zip(param_names, params))
        
        try:
            result = MultiTrendStrategy.run_backtest(df, param_dict, initial_cash)
            
            if 'error' not in result and result['total_trades'] > 0:
                # 优化目标: 收益 - 回撤惩罚 - 交易次数惩罚
                score = result['total_return'] - 0.5 * abs(result['max_drawdown']) - 0.001 * result['total_trades']
                result['score'] = score
                result['params'] = param_dict
                results.append(result)
        except Exception as e:
            continue
        
        if (idx + 1) % 10 == 0:
            print(f"进度: {idx + 1}/{total}")
    
    if not results:
        return {'error': '无有效结果'}
    
    # 按score排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'best_params': results[0]['params'],
        'best_score': results[0]['score'],
        'best_result': results[0],
        'all_results': results[:10],  # 返回top10
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="多空切换策略回测")
    parser.add_argument("--symbol", default="BTC-USDT", help="交易对")
    parser.add_argument("--timeframe", default="15m", help="时间框架")
    parser.add_argument("--start", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10000, help="初始资金")
    parser.add_argument("--optimize", action="store_true", help="是否优化参数")
    args = parser.parse_args()
    
    # 获取数据
    start_ts = int(datetime.strptime(args.start, "%Y-%m-%d").timestamp() * 1000) if args.start else None
    end_ts = int(datetime.strptime(args.end, "%Y-%m-%d").timestamp() * 1000) if args.end else None
    
    print(f"获取 {args.symbol} 数据...")
    df = OKXDataFetcher.fetch_candles(args.symbol, args.timeframe, start_ts, end_ts)
    
    if df.empty:
        print("无法获取数据")
        return
    
    print(f"获取到 {len(df)} 条K线数据")
    print(f"数据范围: {df.index[0]} ~ {df.index[-1]}")
    
    if args.optimize:
        # 参数优化
        param_grid = {
            'ma_period_4h': [150, 200, 250],
            'ma_period_15m': [100, 150, 200],
            'rsi_period': [10, 14, 18],
            'rsi_oversold': [25, 30, 35],
            'rsi_overbought': [65, 70, 75],
            'bb_period': [15, 20, 25],
            'bb_std': [1.5, 2, 2.5],
            'stoploss': [0.015, 0.02, 0.025],
            'takeprofit': [0.025, 0.03, 0.04],
        }
        
        opt_result = optimize_params(df, param_grid, args.cash)
        
        print("\n" + "=" * 60)
        print("最优参数")
        print("=" * 60)
        for k, v in opt_result['best_params'].items():
            print(f"  {k}: {v}")
        
        print("\n最优结果:")
        for k, v in opt_result['best_result'].items():
            if k != 'params':
                print(f"  {k}: {v}")
        
        print("\nTop 5 结果:")
        for i, r in enumerate(opt_result['all_results'][:5]):
            print(f"\n--- #{i+1} ---")
            print(f"  score: {r['score']:.4f}")
            print(f"  return: {r['total_return']:.4f}")
            print(f"  max_dd: {r['max_drawdown']:.4f}")
            print(f"  trades: {r['total_trades']}")
            print(f"  win_rate: {r['win_rate']:.2f}")
    else:
        # 单次回测
        result = MultiTrendStrategy.run_backtest(df, MultiTrendStrategy.DEFAULT_PARAMS, args.cash)
        
        print("\n" + "=" * 50)
        print("回测结果 (默认参数)")
        print("=" * 50)
        for k, v in result.items():
            print(f"{k}: {v}")
        print("=" * 50)


if __name__ == "__main__":
    main()
