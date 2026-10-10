from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import EconomicEvent, FinancialNews
from data_ingestion.news_worker import get_source_status

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
            "source_url": row.source_url,
            "impact_level": row.impact_level,
            "impact_stars": row.impact_stars,
            "classification_status": row.classification_status,
            "revision_no": row.revision_no,
            "sentiment_score": float(row.sentiment_score) if row.sentiment_score is not None else None,
            "ai_analysis_summary": row.ai_analysis_summary,
        }
        for row in rows
    ]


@router.get("/events")
async def list_economic_events(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    rows = (
        await session.scalars(
            select(EconomicEvent)
            .order_by(EconomicEvent.event_timestamp.desc().nulls_last(), EconomicEvent.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "source": row.source,
            "title": row.title,
            "description": row.description,
            "provider_time_raw": row.provider_time_raw,
            "event_timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
            "timezone_status": row.timezone_status,
            "currency": row.currency,
            "previous_value": row.previous_value,
            "forecast_value": row.forecast_value,
            "actual_value": row.actual_value,
            "impact_stars": row.impact_stars,
            "classification_status": row.classification_status,
            "revision_no": row.revision_no,
        }
        for row in rows
    ]


@router.get("/status")
async def news_source_status() -> dict[str, dict[str, object]]:
    return get_source_status()


@router.get("/sentiment")
async def get_news_sentiment(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    rows = (
        await session.scalars(
            select(FinancialNews)
            .where(FinancialNews.sentiment_score.is_not(None))
            .order_by(FinancialNews.published_at.desc())
            .limit(limit)
        )
    ).all()
    if not rows:
        return {
            "score": None,
            "bias": "NEUTRAL",
            "count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
        }
    scores = [float(r.sentiment_score) for r in rows if r.sentiment_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    bull_cnt = sum(1 for s in scores if s > 0.1)
    bear_cnt = sum(1 for s in scores if s < -0.1)
    neu_cnt = len(scores) - bull_cnt - bear_cnt
    bias = "BULLISH" if avg_score > 0.1 else ("BEARISH" if avg_score < -0.1 else "NEUTRAL")

    return {
        "score": avg_score,
        "bias": bias,
        "count": len(scores),
        "bullish_count": bull_cnt,
        "bearish_count": bear_cnt,
        "neutral_count": neu_cnt,
    }


@router.post("/analyze")
async def trigger_news_sentiment_analysis(
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    from ai_engine.sentiment import backfill_news_sentiment

    count = await backfill_news_sentiment(session, batch_size=limit)
    return {"status": "ok", "analyzed_count": count}