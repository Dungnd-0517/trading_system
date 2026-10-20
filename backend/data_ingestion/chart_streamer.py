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
from data_ingestion.market_hours import is_xauusd_trading_hour
from data_ingestion.mt5_feed import MT5Feed
from data_ingestion.mt5_history_seeder import (
    MT5_DATA_START,
    seed_all_mt5_history,
    check_needs_mt5_reseed,
)
from data_ingestion.twelve_data_client import (
    twelve_data_client,
    resolve_twelve_data_symbol,
    TIMEFRAME_TO_TWELVE_DATA,
)

logger = logging.getLogger(__name__)

TIMEFRAMES = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
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

        # Kiểm tra giờ giao dịch chuẩn của XAUUSD
        if symbol == "XAUUSD" and not is_xauusd_trading_hour(timestamp_seconds):
            return []

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
        if raw_symbol in {"PAXGUSDT", "PAXG", "XAUUSD", "XAU/USD", "XAU"}:
            symbol = "XAUUSD"
            close_price = float(item["close"])
            bid = round(close_price - 0.10, 4)
            ask = round(close_price + 0.10, 4)
        elif "/" in raw_symbol:
            symbol = raw_symbol.replace("/", "")
            close_price = float(item["close"])
            bid = close_price
            ask = None
        else:
            symbol = raw_symbol
            close_price = float(item["close"])
            bid = close_price
            ask = None

        time_seconds = timestamp_ms // 1000

        # Kiểm tra giờ giao dịch chuẩn của XAUUSD
        if symbol == "XAUUSD" and not is_xauusd_trading_hour(time_seconds):
            return None

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
    source_symbol: str | None = None,
    interval: str | None = None,
    limit: int = 500,
) -> int:
    """Fetch and persist historical candles from Twelve Data API for target_symbol and timeframe.
    If Twelve Data fails or is offline, synthesizes candles from M1 if timeframe != M1."""
    try:
        count = await twelve_data_client.seed_candles_to_database(
            symbol=target_symbol,
            timeframe=timeframe,
            outputsize=limit,
        )
        if count > 0:
            return count
    except Exception as exc:
        logger.warning("Could not fetch Twelve Data klines for %s %s: %s", target_symbol, timeframe, exc)

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
                    if target_symbol == "XAUUSD" and not is_xauusd_trading_hour(b["open_time"]):
                        continue
                    values = {
                        "symbol": target_symbol,
                        "timeframe": timeframe,
                        "open_time": b["open_time"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                        "data_source": "synthetic",
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
        await self.seed_history_if_needed()
        await self._seed_open_candles()
        await asyncio.gather(self._run_mt5(), self._run_twelve_data_fallback())

    async def seed_history_if_needed(self, target_symbol: str = "XAUUSD") -> None:
        """Nạp lịch sử nến khi khởi động:
        1. Ưu tiên MT5 (từ MT5_DATA_START = 2026-01-01) nếu bridge kết nối được
        2. Fallback về Twelve Data API nếu MT5 không khả dụng
        """
        mt5_feed = MT5Feed()
        mt5_ok = await mt5_feed.is_connected()

        if mt5_ok:
            logger.info("MT5 bridge connected. Seeding candle history from MT5 (from %s)...", MT5_DATA_START)
            needs_reseed = await check_needs_mt5_reseed(target_symbol)
            if needs_reseed:
                try:
                    result = await seed_all_mt5_history(
                        symbol=target_symbol,
                        from_date=MT5_DATA_START,
                        delete_old=True,
                    )
                    logger.info("MT5 history seeding result: %s", result)
                except Exception as exc:
                    logger.error("MT5 history seeding failed, falling back to Twelve Data: %s", exc)
                    await self._seed_twelve_data_history_fallback(target_symbol)
            else:
                logger.info("MT5 candles already up-to-date. Skipping reseed.")
        else:
            logger.warning(
                "MT5 bridge not connected (mode=unavailable). Falling back to Twelve Data for initial candle seed."
            )
            await self._seed_twelve_data_history_fallback(target_symbol)

    async def _seed_twelve_data_history_fallback(
        self, target_symbol: str = "XAUUSD", symbol: str | None = None
    ) -> None:
        """Fallback: nạp lịch sử nến từ Twelve Data API (Spot Gold XAU/USD) khi MT5 không khả dụng."""
        now_ts = datetime.now(timezone.utc).timestamp()
        for tf, interval in TIMEFRAME_TO_TWELVE_DATA.items():
            interval_secs = TIMEFRAMES.get(tf, 60)
            try:
                async with session_factory() as session:
                    row = (
                        await session.execute(
                            select(
                                func.count(MarketCandle.id),
                                func.max(MarketCandle.open_time),
                            ).where(MarketCandle.symbol == target_symbol, MarketCandle.timeframe == tf)
                        )
                    ).first()
                    count = row[0] if row else 0
                    newest = row[1] if row else None
                    if count and count >= 50 and newest and (now_ts - newest.timestamp()) <= interval_secs * 2.0:
                        continue
                await seed_history_for_timeframe(
                    target_symbol=target_symbol,
                    timeframe=tf,
                    limit=500,
                )
            except Exception as exc:
                logger.warning("Failed to seed Twelve Data history for %s %s: %s", target_symbol, tf, exc)



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

    async def _run_twelve_data_fallback(self) -> None:
        """Fallback realtime stream từ Twelve Data API (Spot Gold XAU/USD).
        Khi MT5 đang hoạt động bình thường (có tick trong 15s gần nhất), Twelve Data ở chế độ chờ (standby)
        để bảo toàn hạn ngạch 8 req/phút và 800 req/ngày.
        Khi MT5 gián đoạn / offline, tự động định kỳ quét nến mới nhất từ Twelve Data (1 req/phút, tuân thủ hạn ngạch).
        """
        last_polled_minute = -1
        while True:
            try:
                now = time.time()
                latest_mt5_tick_ts = max(self._mt5_cursors.values()) if self._mt5_cursors else 0
                mt5_healthy = (now * 1000 - latest_mt5_tick_ts) < 15000

                if mt5_healthy:
                    await asyncio.sleep(5)
                    continue

                # MT5 offline / mất kết nối -> Kích hoạt fallback Twelve Data
                current_minute = int(now // 60)
                if current_minute != last_polled_minute:
                    for sym in ("XAUUSD",):
                        try:
                            candle = await twelve_data_client.get_latest_candle(symbol=sym, timeframe="M1")
                            if candle:
                                kline_item = {
                                    "symbol": sym,
                                    "timestamp": candle["time"] * 1000,
                                    "open": candle["open"],
                                    "high": candle["high"],
                                    "low": candle["low"],
                                    "close": candle["close"],
                                    "volume": candle.get("volume", 0.0),
                                }
                                events = self.aggregator.ingest_kline(kline_item)
                                if events:
                                    await self._emit(list(events) if isinstance(events, list) else [events])
                        except Exception as sym_err:
                            logger.debug("Twelve Data fallback error for %s: %s", sym, sym_err)
                    last_polled_minute = current_minute

                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Twelve Data fallback loop exception: %s", exc)
                await asyncio.sleep(10)




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
                    candle_time = int(candle["time"])
                    if str(event["symbol"]) == "XAUUSD" and not is_xauusd_trading_hour(candle_time):
                        continue
                    values = {
                        "symbol": str(event["symbol"]),
                        "timeframe": str(event["timeframe"]),
                        "open_time": datetime.fromtimestamp(candle_time, timezone.utc),
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