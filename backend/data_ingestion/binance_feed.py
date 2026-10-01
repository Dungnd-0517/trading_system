import json
from collections.abc import AsyncIterator

from websockets.asyncio.client import connect


async def stream_klines(symbol: str = "btcusdt", interval: str = "1m") -> AsyncIterator[dict]:
    stream = f"{symbol.lower()}@kline_{interval}"
    url = f"wss://stream.binance.com:9443/ws/{stream}"
    async with connect(url, ping_interval=20, ping_timeout=20) as socket:
        async for message in socket:
            payload = json.loads(message)
            candle = payload.get("k", {})
            yield {
                "symbol": symbol.upper(),
                "timestamp": int(candle.get("t", 0)),
                "open": float(candle.get("o", 0)),
                "high": float(candle.get("h", 0)),
                "low": float(candle.get("l", 0)),
                "close": float(candle.get("c", 0)),
                "volume": float(candle.get("v", 0)),
                "closed": bool(candle.get("x", False)),
            }