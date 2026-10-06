from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import MarketCandle
from data_ingestion.chart_streamer import TIMEFRAME_TO_BINANCE_INTERVAL, seed_history_for_timeframe

router = APIRouter()


@router.get("/history")
async def history(
    symbol: str = "XAUUSD",
    timeframe: str = "M1",
    limit: int = Query(default=500, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    query = (
        select(MarketCandle)
        .where(MarketCandle.symbol == symbol, MarketCandle.timeframe == timeframe)
        .order_by(MarketCandle.open_time.desc())
        .limit(limit)
    )
    rows = (await session.scalars(query)).all()

    # Tự động nạp nến lịch sử nếu DB chưa có dữ liệu cho khung thời gian này
    if not rows and timeframe in TIMEFRAME_TO_BINANCE_INTERVAL:
        binance_symbol = "PAXGUSDT" if symbol.upper() in {"XAUUSD", "PAXG", "PAXGUSDT"} else symbol.upper()
        await seed_history_for_timeframe(
            target_symbol=symbol,
            timeframe=timeframe,
            source_symbol=binance_symbol,
            interval=TIMEFRAME_TO_BINANCE_INTERVAL[timeframe],
            limit=limit,
        )
        rows = (await session.scalars(query)).all()

    return [
        {
            "time": int(row.open_time.timestamp()),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        }
        for row in reversed(rows)
    ]