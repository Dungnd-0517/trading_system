from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import MarketCandle

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