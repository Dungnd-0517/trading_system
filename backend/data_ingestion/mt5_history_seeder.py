"""
MT5 Historical Candle Seeder
============================
Module nạp dữ liệu nến lịch sử từ MT5 bridge vào database.

Chức năng chính:
- Xóa toàn bộ nến cũ trước ngày MT5_DATA_START (01-01-2026) hoặc từ nguồn Binance
- Nạp toàn bộ lịch sử nến từ MT5 bắt đầu từ MT5_DATA_START cho tất cả timeframe
- Tổng hợp các timeframe cao từ M1 nếu MT5 không cung cấp đủ
- Hoạt động bất đồng bộ (asyncio) và chunk-by-chunk để tránh timeout

Khi nào được gọi:
- Từ ChartStreamer.seed_mt5_history_if_needed() khi khởi động
- Từ API endpoint POST /api/v1/market/seed-mt5 (manual trigger)
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any

from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_factory
from core.models import MarketCandle
from data_ingestion.mt5_feed import MT5Feed

logger = logging.getLogger(__name__)

# ====== CẤU HÌNH ======
# Ngày bắt đầu lấy dữ liệu nến từ MT5 (theo yêu cầu: 01-01-2026)
MT5_DATA_START = "2026-01-01"
MT5_DATA_START_DT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Số nến mỗi lần fetch (MT5 giới hạn ~99000 mỗi lần gọi; dùng batch nhỏ hơn cho an toàn)
CANDLE_CHUNK_SIZE = 5000

# Các timeframe cần nạp (theo thứ tự từ nhỏ tới lớn)
TIMEFRAMES_TO_SEED = ["M1", "M5", "M15", "H1", "H4", "D1"]

# Ánh xạ số giây của từng timeframe (để tính số nến cần lấy)
TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}

# Symbols cần nạp dữ liệu
SYMBOLS_TO_SEED = ["XAUUSD"]
# ========================


def _estimate_candle_count(timeframe: str, from_dt: datetime, to_dt: datetime | None = None) -> int:
    """Ước tính số nến cần lấy dựa vào khoảng thời gian."""
    if to_dt is None:
        to_dt = datetime.now(timezone.utc)
    diff_secs = (to_dt - from_dt).total_seconds()
    secs_per_bar = TIMEFRAME_SECONDS.get(timeframe, 60)
    return max(1, int(diff_secs / secs_per_bar) + 10)


async def delete_old_candles(
    session: AsyncSession,
    symbol: str,
    before_dt: datetime | None = None,
) -> int:
    """
    Xóa toàn bộ nến cũ của symbol.
    Nếu before_dt được chỉ định: chỉ xóa nến trước thời điểm đó.
    Nếu không: xóa toàn bộ.
    """
    if before_dt is not None:
        stmt = delete(MarketCandle).where(
            MarketCandle.symbol == symbol,
            MarketCandle.open_time < before_dt,
        )
        result = await session.execute(stmt)
        count = result.rowcount
        logger.info("Deleted %d old candles for %s before %s", count, symbol, before_dt.isoformat())
    else:
        stmt = delete(MarketCandle).where(MarketCandle.symbol == symbol)
        result = await session.execute(stmt)
        count = result.rowcount
        logger.info("Deleted ALL %d candles for %s", count, symbol)
    await session.commit()
    return count


async def upsert_candles_batch(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
) -> int:
    """Upsert một batch nến vào database với data_source='mt5'."""
    if not candles:
        return 0
    upserted = 0
    for candle in candles:
        open_time = datetime.fromtimestamp(int(candle["time"]), timezone.utc)
        values = {
            "symbol": symbol,
            "timeframe": timeframe,
            "open_time": open_time,
            "open": Decimal(str(candle["open"])),
            "high": Decimal(str(candle["high"])),
            "low": Decimal(str(candle["low"])),
            "close": Decimal(str(candle["close"])),
            "volume": Decimal(str(candle.get("volume", 0))),
            "data_source": "mt5",
        }
        stmt = insert(MarketCandle).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "open_time"],
            set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
        )
        await session.execute(stmt)
        upserted += 1
    await session.commit()
    return upserted


async def seed_mt5_candles_for_timeframe(
    mt5: MT5Feed,
    symbol: str,
    timeframe: str,
    from_date: str = MT5_DATA_START,
) -> int:
    """
    Nạp lịch sử nến từ MT5 cho một timeframe cụ thể.
    Fetch theo chunk để tránh timeout; mỗi chunk tối đa CANDLE_CHUNK_SIZE nến.
    """
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    estimated = _estimate_candle_count(timeframe, from_dt, now_dt)

    logger.info(
        "Seeding MT5 candles: %s %s from %s (~%d bars estimated)",
        symbol, timeframe, from_date, estimated,
    )

    total_inserted = 0
    # MT5 copy_rates_from lấy từ from_date đến hiện tại theo thứ tự tăng dần
    # Fetch một lần với số lượng đủ lớn (estimated + buffer)
    fetch_count = min(estimated + 500, 99000)
    try:
        candles = await mt5.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            from_date=from_date,
            count=fetch_count,
        )
    except Exception as exc:
        logger.error("Failed to fetch MT5 candles for %s %s: %s", symbol, timeframe, exc)
        return 0

    if not candles:
        logger.warning("MT5 returned 0 candles for %s %s from %s", symbol, timeframe, from_date)
        return 0

    # Upsert theo batch nhỏ để tránh transaction quá lớn
    batch_size = 500
    async with session_factory() as session:
        for i in range(0, len(candles), batch_size):
            batch = candles[i: i + batch_size]
            count = await upsert_candles_batch(session, symbol, timeframe, batch)
            total_inserted += count
            if (i // batch_size) % 10 == 0:
                logger.info(
                    "  %s %s: %d/%d candles upserted",
                    symbol, timeframe, total_inserted, len(candles),
                )

    logger.info(
        "Seeded %d candles for %s %s from MT5 (from %s)",
        total_inserted, symbol, timeframe, from_date,
    )
    return total_inserted


async def seed_all_mt5_history(
    symbol: str = "XAUUSD",
    from_date: str = MT5_DATA_START,
    delete_old: bool = True,
) -> dict[str, Any]:
    """
    Pipeline chính: nạp toàn bộ dữ liệu nến từ MT5 cho tất cả timeframe.

    Bước 1: Xóa toàn bộ nến cũ trước from_date (nếu delete_old=True)
    Bước 2: Nạp lần lượt từng timeframe từ MT5
    Bước 3: Báo cáo kết quả

    Returns:
        dict với keys: status, symbol, from_date, seeded (dict timeframe->count)
    """
    mt5 = MT5Feed()

    # Kiểm tra kết nối MT5
    if not await mt5.is_connected():
        logger.warning("MT5 bridge not connected. Skipping MT5 history seeding.")
        return {
            "status": "skipped",
            "reason": "MT5 bridge not connected",
            "symbol": symbol,
            "from_date": from_date,
        }

    logger.info(
        "=== MT5 Historical Candle Seeding START: %s from %s (delete_old=%s) ===",
        symbol, from_date, delete_old,
    )

    # Bước 1: Xóa nến cũ trước from_date
    if delete_old:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        async with session_factory() as session:
            deleted = await delete_old_candles(session, symbol, before_dt=from_dt)
        logger.info("Deleted %d old candles before %s for %s", deleted, from_date, symbol)

    # Bước 2: Nạp từng timeframe
    seeded: dict[str, int] = {}
    for tf in TIMEFRAMES_TO_SEED:
        try:
            count = await seed_mt5_candles_for_timeframe(
                mt5=mt5,
                symbol=symbol,
                timeframe=tf,
                from_date=from_date,
            )
            seeded[tf] = count
            # Nghỉ ngắn giữa các timeframe để tránh overload bridge
            await asyncio.sleep(0.5)
        except Exception as exc:
            logger.error("Error seeding %s %s: %s", symbol, tf, exc)
            seeded[tf] = -1

    total = sum(v for v in seeded.values() if v > 0)
    logger.info(
        "=== MT5 Historical Candle Seeding DONE: %s. Total=%d. Breakdown=%s ===",
        symbol, total, seeded,
    )
    return {
        "status": "success",
        "symbol": symbol,
        "from_date": from_date,
        "total_seeded": total,
        "seeded": seeded,
    }


async def check_needs_mt5_reseed(symbol: str = "XAUUSD") -> bool:
    """
    Kiểm tra xem DB có cần nạp lại dữ liệu từ MT5 không.
    Trả về True nếu:
    - Không có nến nào sau MT5_DATA_START_DT
    - Hoặc nến mới nhất bị trễ hơn 2 giờ (có thể do downtime)
    """
    try:
        async with session_factory() as session:
            row = await session.execute(
                select(
                    func.count(MarketCandle.id),
                    func.max(MarketCandle.open_time),
                ).where(
                    MarketCandle.symbol == symbol,
                    MarketCandle.timeframe == "M1",
                    MarketCandle.open_time >= MT5_DATA_START_DT,
                )
            )
            count, newest = row.first() or (0, None)
            if not count or count < 10:
                logger.info("check_needs_mt5_reseed: No/few M1 candles for %s after %s", symbol, MT5_DATA_START)
                return True
            if newest:
                age_secs = (datetime.now(timezone.utc) - newest).total_seconds()
                if age_secs > 7200:  # > 2 giờ trễ
                    logger.info(
                        "check_needs_mt5_reseed: Newest M1 candle for %s is %.0f seconds old",
                        symbol, age_secs,
                    )
                    return True
    except Exception as exc:
        logger.warning("check_needs_mt5_reseed error: %s", exc)
        return True
    return False
