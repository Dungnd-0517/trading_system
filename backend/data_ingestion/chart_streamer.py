import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from core.database import session_factory
from core.models import MarketCandle
from core.redis_client import client as redis_client
from data_ingestion.binance_feed import stream_klines
from data_ingestion.mt5_feed import MT5Feed

logger = logging.getLogger(__name__)

TIMEFRAMES = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}


class CandleAggregator:
    def __init__(self, timeframes: dict[str, int] | None = None) -> None:
        self.timeframes = timeframes or TIMEFRAMES
        self._candles: dict[tuple[str, str], dict[str, float | int]] = {}
        self._seen_ticks: dict[str, set[tuple[int, float, float]]] = {}
        self._tick_order: dict[str, deque[tuple[int, float, float]]] = {}
        self._last_timestamp_ms: dict[str, int] = {}

    def seed(self, symbol: str, timeframe: str, candle: dict[str, float | int]) -> None:
        self._candles[(symbol, timeframe)] = dict(candle)

    def ingest_tick(
        self, symbol: str, timestamp_ms: int, bid: float, ask: float
    ) -> list[dict[str, object]]:
        quote = (timestamp_ms, bid, ask)
        seen = self._seen_ticks.setdefault(symbol, set())
        order = self._tick_order.setdefault(symbol, deque())
        if quote in seen or timestamp_ms < self._last_timestamp_ms.get(symbol, -1):
            return []
        if bid <= 0 or ask < bid:
            return []
        seen.add(quote)
        order.append(quote)
        if len(order) > 4096:
            seen.discard(order.popleft())
        self._last_timestamp_ms[symbol] = max(timestamp_ms, self._last_timestamp_ms.get(symbol, -1))
        timestamp_seconds = timestamp_ms // 1000
        events: list[dict[str, object]] = []

        for timeframe, seconds in self.timeframes.items():
            bucket = timestamp_seconds - timestamp_seconds % seconds
            key = (symbol, timeframe)
            candle = self._candles.get(key)
            if candle is None or bucket > int(candle["time"]):
                candle = {
                    "time": bucket,
                    "open": bid,
                    "high": bid,
                    "low": bid,
                    "close": bid,
                    "volume": 1,
                }
                self._candles[key] = candle
            elif bucket < int(candle["time"]):
                continue
            else:
                candle["high"] = max(float(candle["high"]), bid)
                candle["low"] = min(float(candle["low"]), bid)
                candle["close"] = bid
                candle["volume"] = int(candle["volume"]) + 1
            events.append(self._event(symbol, timeframe, candle, bid, ask, "tick_count"))
        return events

    def ingest_kline(self, item: dict[str, Any]) -> dict[str, object] | None:
        symbol = str(item.get("symbol") or "").upper()
        timestamp_ms = int(item.get("timestamp") or 0)
        if not symbol or timestamp_ms <= 0:
            return None
        time_seconds = timestamp_ms // 1000
        candle = {
            "time": time_seconds,
            "open": float(item["open"]),
            "high": float(item["high"]),
            "low": float(item["low"]),
            "close": float(item["close"]),
            "volume": float(item["volume"]),
        }
        self._candles[(symbol, "M1")] = candle
        return self._event(
            symbol,
            "M1",
            candle,
            float(item["close"]),
            None,
            "base_asset_quantity",
        )

    @staticmethod
    def _event(
        symbol: str,
        timeframe: str,
        candle: dict[str, float | int],
        bid: float,
        ask: float | None,
        volume_unit: str,
    ) -> dict[str, object]:
        timestamp = int(candle["time"])
        close = float(candle["close"])
        opened = float(candle["open"])
        price: dict[str, float] = {"value": bid}
        if ask is not None:
            price["bid"] = bid
            price["ask"] = ask
        return {
            "type": "chart.update",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": timestamp,
            "candle": {
                "time": timestamp,
                "open": opened,
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": close,
            },
            "volume": {
                "time": timestamp,
                "value": float(candle["volume"]),
                "unit": volume_unit,
                "color": "up" if close >= opened else "down",
            },
            "price": price,
        }


class ChartStreamer:
    def __init__(self) -> None:
        self.aggregator = CandleAggregator()
        self.mt5 = MT5Feed()
        self.symbols = ("XAUUSD", "EURUSD", "GBPUSD")
        self._mt5_cursors = {symbol: max(0, int(time.time() * 1000) - 2000) for symbol in self.symbols}

    async def run(self) -> None:
        await self._seed_open_candles()
        await asyncio.gather(self._run_mt5(), self._run_binance())

    async def _seed_open_candles(self) -> None:
        async with session_factory() as session:
            for symbol in self.symbols:
                for timeframe in TIMEFRAMES:
                    row = await session.scalar(
                        select(MarketCandle)
                        .where(MarketCandle.symbol == symbol, MarketCandle.timeframe == timeframe)
                        .order_by(MarketCandle.open_time.desc())
                        .limit(1)
                    )
                    if row is None:
                        continue
                    self.aggregator.seed(
                        symbol,
                        timeframe,
                        {
                            "time": int(row.open_time.timestamp()),
                            "open": float(row.open),
                            "high": float(row.high),
                            "low": float(row.low),
                            "close": float(row.close),
                            "volume": float(row.volume),
                        },
                    )

    async def _run_mt5(self) -> None:
        while True:
            for symbol in self.symbols:
                try:
                    ticks = await self.mt5.ticks_since(symbol, self._mt5_cursors[symbol])
                    events = []
                    for tick in ticks:
                        timestamp_ms = int(tick["timestamp"])
                        self._mt5_cursors[symbol] = max(self._mt5_cursors[symbol], timestamp_ms)
                        events.extend(
                            self.aggregator.ingest_tick(
                                symbol,
                                timestamp_ms,
                                float(tick["bid"]),
                                float(tick["ask"]),
                            )
                        )
                    await self._emit(events)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.debug("MT5 tick unavailable for %s: %s", symbol, exc)
            await asyncio.sleep(0.25)

    async def _run_binance(self) -> None:
        while True:
            try:
                async for candle in stream_klines("btcusdt", "1m"):
                    event = self.aggregator.ingest_kline(candle)
                    if event is not None:
                        await self._emit([event])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Binance kline stream disconnected: %s", exc)
                await asyncio.sleep(5)

    async def _emit(self, events: list[dict[str, object]]) -> None:
        if not events:
            return
        try:
            async with session_factory() as session:
                for event in events:
                    candle = event["candle"]
                    volume = event["volume"]
                    assert isinstance(candle, dict)
                    assert isinstance(volume, dict)
                    values = {
                        "symbol": str(event["symbol"]),
                        "timeframe": str(event["timeframe"]),
                        "open_time": datetime.fromtimestamp(int(candle["time"]), timezone.utc),
                        "open": candle["open"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "close": candle["close"],
                        "volume": volume["value"],
                    }
                    statement = insert(MarketCandle).values(**values)
                    statement = statement.on_conflict_do_update(
                        index_elements=["symbol", "timeframe", "open_time"],
                        set_={
                            key: value
                            for key, value in values.items()
                            if key not in {"symbol", "timeframe", "open_time"}
                        },
                    )
                    await session.execute(statement)
                await session.commit()
        except Exception:
            logger.exception("Market candle transaction failed")
            return
        for event in events:
            try:
                await redis_client.publish("market:ticks", json.dumps(event, separators=(",", ":")))
            except Exception:
                logger.exception("Could not publish chart update")