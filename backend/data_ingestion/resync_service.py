"""
Candle Resync and Cache Purge Service
======================================
Thực hiện Full Resync dữ liệu nến cho XAUUSD:
1. Purge Data cũ: Xóa toàn bộ dữ liệu nến rác của cặp XAUUSD trên tất cả timeframe.
2. Xóa Cache Redis: Clear toàn bộ cache nến trên Redis (twelve_data:cache:*).
3. Lấy lại mảng nến lịch sử chuẩn từ MT5 Bridge (nếu có kết nối) hoặc Twelve Data REST API.
   - Bỏ hoàn toàn auto-fill / interpolate nến rỗng.
   - Loại bỏ các nến rơi vào khung giờ đóng cửa của XAUUSD (Weekend: T6 21:00 UTC -> CN 22:00 UTC, Daily Break: 21:00 - 22:00 UTC).
4. Lưu nến chuẩn vào Database (MarketCandle).
5. Phát tín hiệu WebSocket REFRESH_CHART xuống client qua Redis Pub/Sub để re-render Canvas Lightweight Charts.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from core.database import session_factory
from core.models import MarketCandle
from core.redis_client import client as redis_client
from data_ingestion.market_hours import is_xauusd_trading_hour
from data_ingestion.mt5_feed import MT5Feed
from data_ingestion.twelve_data_client import TIMEFRAME_TO_TWELVE_DATA, twelve_data_client

logger = logging.getLogger(__name__)

ALL_TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1"]


async def clear_candle_cache() -> int:
    """Xóa toàn bộ Cache nến trên Redis (twelve_data:cache:* và các key liên quan)."""
    deleted_keys = 0
    try:
        keys_to_delete = []
        async for key in redis_client.scan_iter("twelve_data:cache:*"):
            keys_to_delete.append(key)
        async for key in redis_client.scan_iter("market:candles:*"):
            keys_to_delete.append(key)

        if keys_to_delete:
            deleted_keys = await redis_client.delete(*keys_to_delete)
            logger.info("Cleared %d candle cache keys from Redis.", deleted_keys)
    except Exception as exc:
        logger.warning("Error clearing Redis candle cache: %s", exc)
    return deleted_keys


async def purge_old_xauusd_candles(symbol: str = "XAUUSD") -> int:
    """Xóa toàn bộ dữ liệu nến của symbol XAUUSD trên tất cả các timeframe."""
    async with session_factory() as session:
        stmt = delete(MarketCandle).where(MarketCandle.symbol == symbol.upper())
        result = await session.execute(stmt)
        count = result.rowcount
        await session.commit()
    logger.info("Purged %d old candles for %s from database.", count, symbol)
    return count


async def trigger_client_chart_refresh(symbol: str = "XAUUSD") -> None:
    """Phát tín hiệu WebSocket REFRESH_CHART xuống Client qua Redis channel market:ticks."""
    payload = json.dumps({
        "type": "REFRESH_CHART",
        "symbol": symbol.upper(),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    })
    try:
        await redis_client.publish("market:ticks", payload)
        logger.info("Published REFRESH_CHART signal to market:ticks for %s", symbol)
    except Exception as exc:
        logger.warning("Could not publish REFRESH_CHART to Redis: %s", exc)


async def resync_candles_full(
    symbol: str = "XAUUSD",
    outputsize_per_tf: int = 500,
    force_purge: bool = True,
) -> dict[str, Any]:
    """
    Thực hiện quy trình Resync toàn diện dữ liệu nến:
    1. Clear Cache Redis.
    2. Purge sạch dữ liệu nến cũ trong DB nếu force_purge=True.
    3. Nạp lại dữ liệu nến lịch sử chuẩn từ MT5 (nếu connected) hoặc Twelve Data.
       Chỉ lưu các nến thực tế từ broker và nằm trong khung giờ mở cửa.
    4. Kích hoạt REFRESH_CHART broadcast xuống frontend.
    """
    symbol = symbol.upper()
    logger.info("Starting Full Candle Resync for %s (force_purge=%s)...", symbol, force_purge)

    # 1. Clear Redis cache
    cleared_cache = await clear_candle_cache()

    # 2. Purge DB cũ
    purged_count = 0
    if force_purge:
        purged_count = await purge_old_xauusd_candles(symbol)

    # 3. Kiểm tra kết nối MT5
    mt5 = MT5Feed()
    mt5_connected = await mt5.is_connected()
    provider_used = "mt5" if mt5_connected else "twelvedata"
    logger.info("Resync data provider: %s (MT5 connected: %s)", provider_used, mt5_connected)

    seeded_summary: dict[str, int] = {}

    for tf in ALL_TIMEFRAMES:
        tf_count = 0
        if mt5_connected:
            try:
                candles = await mt5.get_latest_candles(symbol=symbol, timeframe=tf, count=outputsize_per_tf)
                if candles:
                    async with session_factory() as session:
                        for c in candles:
                            c_time = int(c["time"])
                            # Lọc giờ đóng cửa của XAUUSD
                            if symbol == "XAUUSD" and not is_xauusd_trading_hour(c_time):
                                continue
                            open_time = datetime.fromtimestamp(c_time, timezone.utc)
                            values = {
                                "symbol": symbol,
                                "timeframe": tf,
                                "open_time": open_time,
                                "open": Decimal(str(c["open"])),
                                "high": Decimal(str(c["high"])),
                                "low": Decimal(str(c["low"])),
                                "close": Decimal(str(c["close"])),
                                "volume": Decimal(str(c.get("volume", 0))),
                                "data_source": "mt5",
                            }
                            stmt = insert(MarketCandle).values(**values)
                            stmt = stmt.on_conflict_do_update(
                                index_elements=["symbol", "timeframe", "open_time"],
                                set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                            )
                            await session.execute(stmt)
                            tf_count += 1
                        await session.commit()
            except Exception as exc:
                logger.warning("MT5 resync failed for %s %s: %s", symbol, tf, exc)

        # Fallback về Twelve Data nếu MT5 không có nến hoặc không kết nối
        if tf_count == 0 and tf in TIMEFRAME_TO_TWELVE_DATA:
            try:
                # Twelve Data: Lấy nến không dùng cache để lấy bản mới nhất chuẩn broker
                raw_candles = await twelve_data_client.fetch_time_series(
                    symbol=symbol,
                    timeframe=tf,
                    outputsize=outputsize_per_tf,
                    use_cache=False,
                )
                if raw_candles:
                    async with session_factory() as session:
                        for c in raw_candles:
                            c_time = int(c["time"])
                            if symbol == "XAUUSD" and not is_xauusd_trading_hour(c_time):
                                continue
                            open_time = datetime.fromtimestamp(c_time, timezone.utc)
                            values = {
                                "symbol": symbol,
                                "timeframe": tf,
                                "open_time": open_time,
                                "open": Decimal(str(c["open"])),
                                "high": Decimal(str(c["high"])),
                                "low": Decimal(str(c["low"])),
                                "close": Decimal(str(c["close"])),
                                "volume": Decimal(str(c.get("volume", 0.0))),
                                "data_source": "twelvedata",
                            }
                            stmt = insert(MarketCandle).values(**values)
                            stmt = stmt.on_conflict_do_update(
                                index_elements=["symbol", "timeframe", "open_time"],
                                set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                            )
                            await session.execute(stmt)
                            tf_count += 1
                        await session.commit()
            except Exception as td_err:
                logger.error("Twelve Data resync failed for %s %s: %s", symbol, tf, td_err)

        seeded_summary[tf] = tf_count
        # Nghỉ ngắn giữa các timeframe để tuân thủ rate limit Twelve Data
        await asyncio.sleep(0.5)

    # 4. Trigger WebSocket REFRESH_CHART xuống client
    await trigger_client_chart_refresh(symbol)

    total_seeded = sum(seeded_summary.values())
    logger.info(
        "Full Resync finished for %s. Provider: %s. Purged: %d. Total Seeded: %d. Breakdown: %s",
        symbol, provider_used, purged_count, total_seeded, seeded_summary,
    )

    return {
        "status": "success",
        "symbol": symbol,
        "provider": provider_used,
        "purged_old_candles": purged_count,
        "cleared_cache_keys": cleared_cache,
        "total_seeded": total_seeded,
        "seeded_by_timeframe": seeded_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
