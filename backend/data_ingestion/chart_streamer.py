import asyncio
import json
from decimal import Decimal
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from core.database import session_factory
from core.models import MarketCandle
from core.redis_client import client as redis_client
from data_ingestion.binance_feed import stream_klines
from data_ingestion.mt5_feed import MT5Feed

logger = logging.getLogger(__name__)

TIMEFRAMES = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}

TIMEFRAME_TO_BINANCE_INTERVAL = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}


class KlineEventList(list):
    """List of chart update events that also provides dict access to the primary (M1) event for backward compatibility."""

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            return self[0][item]
        return super().__getitem__(item)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str) and len(self) > 0 and isinstance(self[0], dict):
            return item in self[0]
        return super().__contains__(item)

    def get(self, key: str, default: Any = None) -> Any:
        if len(self) > 0 and isinstance(self[0], dict):
            return self[0].get(key, default)
        return default


class CandleAggregator:
    def __init__(self, timeframes: dict[str, int] | None = None) -> None:
        self.timeframes = timeframes or TIMEFRAMES
        self._candles: dict[tuple[str, str], dict[str, float | int]] = {}
        self._seen_ticks: dict[str, set[tuple[int, float, float]]] = {}
        self._tick_order: dict[str, deque[tuple[int, float, float]]] = {}
        self._last_timestamp_ms: dict[str, int] = {}
        self._kline_vol_tracker: dict[tuple[str, int], float] = {}

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

    def ingest_kline(self, item: dict[str, Any]) -> KlineEventList | None:
        raw_symbol = str(item.get("symbol") or "").upper()
        timestamp_ms = int(item.get("timestamp") or 0)
        if not raw_symbol or timestamp_ms <= 0:
            return None

        # Symbol mapping & synthetic spread for Gold (D7)
        if raw_symbol in {"PAXGUSDT", "PAXG", "XAUUSD"}:
            symbol = "XAUUSD"
            close_price = float(item["close"])
            bid = round(close_price - 0.10, 4)
            ask = round(close_price + 0.10, 4)
        else:
            symbol = raw_symbol
            close_price = float(item["close"])
            bid = close_price
            ask = None

        time_seconds = timestamp_ms // 1000
        open_val = float(item["open"])
        high_val = float(item["high"])
        low_val = float(item["low"])
        close_val = close_price
        vol_val = float(item["volume"])

        # Track volume delta for this 1m bar
        last_m1_vol = self._kline_vol_tracker.get((symbol, time_seconds), 0.0)
        delta_vol = max(0.0, vol_val - last_m1_vol)
        self._kline_vol_tracker[(symbol, time_seconds)] = vol_val
        if len(self._kline_vol_tracker) > 200:
            oldest_keys = sorted(self._kline_vol_tracker.keys(), key=lambda k: k[1])[:100]
            for k in oldest_keys:
                self._kline_vol_tracker.pop(k, None)

        events: list[dict[str, object]] = []
        for timeframe, seconds in self.timeframes.items():
            bucket = time_seconds - time_seconds % seconds
            key = (symbol, timeframe)
            candle = self._candles.get(key)

            if timeframe == "M1":
                candle = {
                    "time": bucket,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "volume": vol_val,
                }
                self._candles[key] = candle
            else:
                if candle is None or bucket > int(candle["time"]):
                    candle = {
                        "time": bucket,
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val,
                        "volume": vol_val,
                    }
                    self._candles[key] = candle
                elif bucket < int(candle["time"]):
                    continue
                else:
                    candle["high"] = max(float(candle["high"]), high_val)
                    candle["low"] = min(float(candle["low"]), low_val)
                    candle["close"] = close_val
                    candle["volume"] = round(float(candle.get("volume", 0.0)) + delta_vol, 4)

            events.append(self._event(symbol, timeframe, candle, bid, ask, "base_asset_quantity"))

        return KlineEventList(events)

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
        price: dict[str, float] = {"value": close}
        if ask is not None:
            price["bid"] = bid
            price["ask"] = ask
        else:
            price["value"] = bid
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


async def seed_history_for_timeframe(
    target_symbol: str = "XAUUSD",
    timeframe: str = "M1",
    source_symbol: str = "PAXGUSDT",
    interval: str = "1m",
    limit: int = 500,
) -> int:
    """Fetch and persist historical candles from Binance for target_symbol and timeframe.
    If Binance fails or is offline, synthesizes candles from M1 if timeframe != M1."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={source_symbol.upper()}&interval={interval}&limit={min(limit, 1000)}"
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            resp = await http_client.get(url)
            if resp.status_code == 200:
                klines = resp.json()
                async with session_factory() as session:
                    for item in klines:
                        open_time_ms = int(item[0])
                        open_time = datetime.fromtimestamp(open_time_ms / 1000, timezone.utc)
                        values = {
                            "symbol": target_symbol,
                            "timeframe": timeframe,
                            "open_time": open_time,
                            "open": Decimal(str(item[1])),
                            "high": Decimal(str(item[2])),
                            "low": Decimal(str(item[3])),
                            "close": Decimal(str(item[4])),
                            "volume": Decimal(str(item[5])),
                        }
                        stmt = insert(MarketCandle).values(**values)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["symbol", "timeframe", "open_time"],
                            set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                        )
                        await session.execute(stmt)
                    await session.commit()
                logger.info(
                    "Successfully seeded %d historical candles for %s %s from Binance %s (%s)",
                    len(klines),
                    target_symbol,
                    timeframe,
                    source_symbol,
                    interval,
                )
                return len(klines)
    except Exception as exc:
        logger.warning("Could not fetch Binance klines for %s %s: %s", target_symbol, timeframe, exc)

    # Fallback: tổng hợp từ M1 có sẵn trong DB
    if timeframe != "M1" and timeframe in TIMEFRAMES:
        seconds = TIMEFRAMES[timeframe]
        try:
            async with session_factory() as session:
                m1_rows = (
                    await session.scalars(
                        select(MarketCandle)
                        .where(MarketCandle.symbol == target_symbol, MarketCandle.timeframe == "M1")
                        .order_by(MarketCandle.open_time.asc())
                    )
                ).all()
                if not m1_rows:
                    return 0

                buckets: dict[int, dict[str, Any]] = {}
                for row in m1_rows:
                    sec = int(row.open_time.timestamp())
                    b_sec = sec - sec % seconds
                    if b_sec not in buckets:
                        buckets[b_sec] = {
                            "open_time": datetime.fromtimestamp(b_sec, timezone.utc),
                            "open": row.open,
                            "high": row.high,
                            "low": row.low,
                            "close": row.close,
                            "volume": row.volume,
                        }
                    else:
                        b = buckets[b_sec]
                        b["high"] = max(b["high"], row.high)
                        b["low"] = min(b["low"], row.low)
                        b["close"] = row.close
                        b["volume"] += row.volume

                for b in buckets.values():
                    values = {
                        "symbol": target_symbol,
                        "timeframe": timeframe,
                        "open_time": b["open_time"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                    }
                    stmt = insert(MarketCandle).values(**values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["symbol", "timeframe", "open_time"],
                        set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                    )
                    await session.execute(stmt)
                await session.commit()
                logger.info(
                    "Synthesized %d %s candles for %s from M1 candles in DB",
                    len(buckets),
                    timeframe,
                    target_symbol,
                )
                return len(buckets)
        except Exception as exc:
            logger.warning("Failed to synthesize %s candles from M1: %s", timeframe, exc)

    return 0


class ChartStreamer:
    def __init__(self) -> None:
        self.aggregator = CandleAggregator()
        self.mt5 = MT5Feed()
        self.symbols = ("XAUUSD", "EURUSD", "GBPUSD")
        self._mt5_cursors = {symbol: max(0, int(time.time() * 1000) - 2000) for symbol in self.symbols}

    async def run(self) -> None:
        await self.seed_binance_history_if_needed()
        await self._seed_open_candles()
        await asyncio.gather(self._run_mt5(), self._run_binance())

    async def seed_binance_history_if_needed(self, symbol: str = "PAXGUSDT", target_symbol: str = "XAUUSD") -> None:
        for tf, interval in TIMEFRAME_TO_BINANCE_INTERVAL.items():
            try:
                async with session_factory() as session:
                    count = await session.scalar(
                        select(func.count())
                        .select_from(MarketCandle)
                        .where(MarketCandle.symbol == target_symbol, MarketCandle.timeframe == tf)
                    )
                    if count and count >= 50:
                        continue
                await seed_history_for_timeframe(
                    target_symbol=target_symbol,
                    timeframe=tf,
                    source_symbol=symbol,
                    interval=interval,
                    limit=500,
                )
            except Exception as exc:
                logger.warning("Failed to seed Binance history for %s %s: %s", target_symbol, tf, exc)

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

    async def _run_binance_symbol(self, symbol: str) -> None:
        while True:
            try:
                async for candle in stream_klines(symbol, "1m"):
                    events = self.aggregator.ingest_kline(candle)
                    if events:
                        await self._emit(list(events) if isinstance(events, list) else [events])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Binance kline stream for %s disconnected: %s", symbol, exc)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Binance kline stream for %s disconnected: %s", symbol, exc)
                await asyncio.sleep(5)

    async def _run_binance(self) -> None:
        await asyncio.gather(
            self._run_binance_symbol("btcusdt"),
            self._run_binance_symbol("paxgusdt"),
        )

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