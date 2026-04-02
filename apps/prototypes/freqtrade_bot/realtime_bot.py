"""
实时交易机器人 - WebSocket 订阅 + 信号判断 + 下单
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import pandas as pd
import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()


class OKXWebSocketClient:
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    OKX_USE_SANDBOX = os.getenv("OKX_USE_SANDBOX", "true").lower() == "true"

    WS_URL = "wss://wspap.okx.com:8443/ws/v5/public" if OKX_USE_SANDBOX else "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(self):
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.subscriptions: Dict[str, dict] = {}
        self.callbacks: Dict[str, callable] = {}

    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect(self.WS_URL)

    async def subscribe(self, channel: str, inst_id: str, callback: callable):
        sub_key = f"{channel}:{inst_id}"
        subscribe_msg = {
            "op": "subscribe",
            "args": [{"channel": channel, "instId": inst_id}],
        }
        await self.ws.send_json(subscribe_msg)
        self.subscriptions[sub_key] = {"channel": channel, "instId": inst_id}
        self.callbacks[sub_key] = callback

    async def listen(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("arg", {}).get("channel"):
                    sub_key = f"{data['arg']['channel']}:{data['arg']['instId']}"
                    if sub_key in self.callbacks and "data" in data:
                        await self.callbacks[sub_key](data["data"])
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()


class TradingBot:
    BUY_THRESHOLD = 0.7
    SELL_THRESHOLD = 1.5
    VOLUME_MA_WINDOW = 20

    def __init__(self, symbols: List[str], timeframe: str = "1m"):
        self.ws_client = OKXWebSocketClient()
        self.symbols = symbols
        self.timeframe = timeframe
        self.candle_data: Dict[str, pd.DataFrame] = {}
        self.volume_history: Dict[str, List[float]] = {}
        self.current_positions: Dict[str, dict] = {}

    async def initialize(self):
        await self.ws_client.connect()

        for symbol in self.symbols:
            self.candle_data[symbol] = pd.DataFrame()
            self.volume_history[symbol] = []

            await self.ws_client.subscribe("candles", symbol, lambda data, s=symbol: self.on_candle(s, data))
            await self.ws_client.subscribe("tickers", symbol, lambda data, s=symbol: self.on_ticker(s, data))

    async def on_candle(self, symbol: str, data: List):
        for candle in data:
            ts = datetime.fromtimestamp(int(candle[0]) / 1000)
            row = {
                "timestamp": ts,
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }

            if symbol not in self.candle_data or self.candle_data[symbol].empty:
                self.candle_data[symbol] = pd.DataFrame([row])
            else:
                self.candle_data[symbol] = pd.concat(
                    [self.candle_data[symbol], pd.DataFrame([row])], ignore_index=True
                )

                window = min(self.VOLUME_MA_WINDOW, len(self.candle_data[symbol]))
                if window > 1:
                    recent = self.candle_data[symbol].tail(window)
                    current_vol = row["volume"]
                    avg_vol = recent["volume"].mean()
                    volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

                    price_change = (row["close"] - recent["close"].iloc[-2]) / recent["close"].iloc[-2] if len(recent) > 1 else 0

                    signal = self.check_signal(volume_ratio, price_change)
                    if signal:
                        await self.execute_trade(symbol, signal, row["close"])

    def check_signal(self, volume_ratio: float, price_change: float) -> Optional[str]:
        if volume_ratio < self.BUY_THRESHOLD and price_change < 0:
            return "BUY"
        elif volume_ratio > self.SELL_THRESHOLD and price_change > 0:
            return "SELL"
        return None

    async def execute_trade(self, symbol: str, signal: str, price: float):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {signal} signal for {symbol} at {price}")

        if signal == "BUY" and symbol not in self.current_positions:
            self.current_positions[symbol] = {
                "entry_price": price,
                "entry_time": datetime.now(),
                "side": "long",
            }
            print(f"  -> 开多仓: {symbol} @ {price}")

        elif signal == "SELL" and symbol in self.current_positions:
            entry_price = self.current_positions[symbol]["entry_price"]
            pnl = (price - entry_price) / entry_price
            print(f"  -> 平仓: {symbol} @ {price}, PnL: {pnl*100:.2f}%")
            del self.current_positions[symbol]

    async def on_ticker(self, symbol: str, data: List):
        pass

    async def run(self):
        await self.initialize()
        await self.ws_client.listen()

    async def stop(self):
        await self.ws_client.close()


async def main():
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    bot = TradingBot(symbols=symbols, timeframe="1m")

    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
