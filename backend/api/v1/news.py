from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import FinancialNews

router = APIRouter()


@router.get("")
async def list_news(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    rows = (
        await session.scalars(
            select(FinancialNews)
            .order_by(FinancialNews.published_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "source": row.source,
            "title": row.title,
            "published_at": row.published_at.isoformat(),
            "impact_level": row.impact_level,
            "sentiment_score": float(row.sentiment_score) if row.sentiment_score is not None else None,
            "ai_analysis_summary": row.ai_analysis_summary,
        }
        for row in rows
    ]