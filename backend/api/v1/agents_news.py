from typing import Any
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_agent import (
    MacroInsightReport,
    news_event_agent,
)
from core.database import session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_db_session():
    async with session_factory() as session:
        yield session


@router.get("/macro-report", response_model=MacroInsightReport)
async def get_macro_report(session: AsyncSession = Depends(get_db_session)) -> MacroInsightReport:
    """
    Lấy báo cáo phân tích vĩ mô, điểm cảm xúc tổng hợp và trạng thái Circuit Breaker mới nhất từ News & Event Agent.
    """
    return await news_event_agent.generate_macro_report(session=session)


@router.post("/trigger-scan")
async def trigger_news_scan() -> dict[str, Any]:
    """
    Kích hoạt quét tin tức và lịch kinh tế ngay lập tức thông qua News Collector Controller.
    """
    return await news_event_agent.trigger_scan()


@router.get("/circuit-breaker-status")
async def get_circuit_breaker_status(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Kiểm tra chi tiết trạng thái Circuit Breaker hiện tại, lý do ngắt mạch và đồng hồ đếm ngược.
    """
    return await news_event_agent.get_circuit_breaker_status(session=session)
