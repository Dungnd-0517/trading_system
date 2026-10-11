from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient

from ai_engine.news_agent import (
    MacroInsightReport,
    NewsEventAgent,
    news_event_agent,
)
from core.database import session_factory
from core.models import EconomicEvent, FinancialNews
from main import app


@pytest.mark.anyio
async def test_generate_macro_report_default_environment():
    """Kiểm tra sinh báo cáo MacroInsightReport trong điều kiện bình thường"""
    async with session_factory() as session:
        report = await news_event_agent.generate_macro_report(session=session, broadcast=False)

        assert isinstance(report, MacroInsightReport)
        assert report.agent == "NEWS_AND_EVENT_AGENT"
        assert -1.0 <= report.macro_sentiment_score <= 1.0
        assert report.macro_bias in {"BULLISH_GOLD", "BEARISH_GOLD", "NEUTRAL"}
        assert report.dxy_correlation_bias in {"BULLISH_DXY", "BEARISH_DXY", "NEUTRAL"}
        assert isinstance(report.active_circuit_breaker, bool)
        assert report.recommendation_for_governor.action in {
            "HALT_NEW_ORDERS",
            "TIGHTEN_RISK",
            "NORMAL_OPERATION",
        }
        assert report.recommended_poll_interval_seconds in {60, 300}


@pytest.mark.anyio
async def test_generate_macro_report_with_circuit_breaker_active():
    """Kiểm tra kích hoạt cờ Circuit Breaker và khuyến nghị ngắt lệnh khi có tin 3 sao USD"""
    now = datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc)
    event_time = now + timedelta(minutes=15)

    async with session_factory() as session:
        # Thêm sự kiện test 3 sao USD trong phạm vi 15 phút
        test_event = EconomicEvent(
            source="fair_economy",
            title="TEST US Non-Farm Employment Change",
            provider_time_raw="14:15",
            event_timestamp=event_time,
            currency="USD",
            impact_stars=3,
            classification_status="CLASSIFIED",
            timezone_status="VERIFIED",
            revision_no=1,
        )
        session.add(test_event)
        await session.commit()

        report = await news_event_agent.generate_macro_report(
            session=session, target_time=now, broadcast=False
        )

        assert report.active_circuit_breaker is True
        assert report.circuit_breaker_details is not None
        assert report.circuit_breaker_details.status == "HALT_ACTIVE"
        assert report.circuit_breaker_details.impact_stars == 3
        assert "TEST US Non-Farm" in report.circuit_breaker_details.event_name
        assert report.recommendation_for_governor.action == "HALT_NEW_ORDERS"
        assert report.recommendation_for_governor.suggested_risk_scale == 0.0
        # Tần suất polling tự động chuyển sang 60s khi áp sát tin 3 sao
        assert report.recommended_poll_interval_seconds == 60


@pytest.mark.anyio
async def test_generate_macro_report_with_bullish_gold_sentiment():
    """Kiểm tra phân tích cảm xúc tin tức Bullish cho Vàng và đảo nghịch Bearish cho DXY"""
    now = datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc)
    pub_time = now - timedelta(hours=1)

    async with session_factory() as session:
        # Thêm tin tức ủng hộ Vàng tăng giá
        test_news = FinancialNews(
            source="Kitco News",
            title="TEST Gold rallies as safe-haven demand surges amid Middle East geopolitical tensions",
            content="Investors rush to bullion as conflict escalates, driving Treasury yields lower and weakening the Dollar.",
            published_at=pub_time,
            impact_stars=3,
            impact_level="HIGH",
            classification_status="CLASSIFIED",
            sentiment_score=Decimal("0.75"),
            ai_analysis_summary="Strong bullish safe-haven demand for Gold.",
            revision_no=1,
        )
        session.add(test_news)
        await session.commit()

        report = await news_event_agent.generate_macro_report(
            session=session, target_time=now, broadcast=False
        )

        assert report.macro_sentiment_score > 0.25
        assert report.macro_bias == "BULLISH_GOLD"
        assert report.dxy_correlation_bias == "BEARISH_DXY"
        # Báo cáo phát hiện tin breaking khẩn cấp
        assert len(report.breaking_news_alerts) >= 1
        assert any("Middle East" in a.headline for a in report.breaking_news_alerts)


@pytest.mark.anyio
async def test_calculate_event_surprise_impact():
    """Kiểm tra thuật toán đo lường Surprise Factor từ dữ liệu kinh tế Actual vs Forecast"""
    agent = NewsEventAgent()

    # Nhóm 1: CPI thực tế cao hơn dự báo (+20%) -> Tốt cho USD -> Xấu cho Vàng (-0.35)
    cpi_beat = [
        EconomicEvent(
            source="test",
            title="US Core CPI m/m",
            actual_value="0.6%",
            forecast_value="0.3%",
            impact_stars=3,
            currency="USD",
            provider_time_raw="14:30",
        )
    ]
    impact_cpi_beat = agent._calculate_event_surprise_impact(cpi_beat)
    assert impact_cpi_beat < 0  # Xấu cho Vàng

    # Nhóm 2: NFP thực tế thấp hơn dự báo -> Xấu cho USD -> Tốt cho Vàng (+0.35)
    nfp_miss = [
        EconomicEvent(
            source="test",
            title="Non-Farm Payrolls",
            actual_value="110K",
            forecast_value="180K",
            impact_stars=3,
            currency="USD",
            provider_time_raw="14:30",
        )
    ]
    impact_nfp_miss = agent._calculate_event_surprise_impact(nfp_miss)
    assert impact_nfp_miss > 0  # Tốt cho Vàng


@pytest.mark.anyio
async def test_news_agent_rest_api_endpoints():
    """Kiểm tra 3 REST API endpoints của News & Event Agent: /macro-report, /circuit-breaker-status, /trigger-scan"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/agents/news/macro-report
        resp_macro = await client.get("/api/v1/agents/news/macro-report")
        assert resp_macro.status_code == 200
        data_macro = resp_macro.json()
        assert data_macro["agent"] == "NEWS_AND_EVENT_AGENT"
        assert "macro_sentiment_score" in data_macro
        assert "macro_bias" in data_macro
        assert "recommendation_for_governor" in data_macro

        # 2. GET /api/v1/agents/news/circuit-breaker-status
        resp_cb = await client.get("/api/v1/agents/news/circuit-breaker-status")
        assert resp_cb.status_code == 200
        data_cb = resp_cb.json()
        assert "circuit_breaker_enabled" in data_cb
        assert "is_active" in data_cb
        assert "buffer_mins" in data_cb

        # 3. POST /api/v1/agents/news/trigger-scan
        resp_scan = await client.post("/api/v1/agents/news/trigger-scan")
        assert resp_scan.status_code == 200
        data_scan = resp_scan.json()
        assert "scanned_at" in data_scan
        assert data_scan["status"] in {"COMPLETED", "PARTIAL_SUCCESS"}
