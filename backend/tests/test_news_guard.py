from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import delete

from ai_engine.news_guard import NewsCircuitBreaker
from core.database import engine, session_factory
from core.models import EconomicEvent, SystemTradingConfig




@pytest.mark.anyio
async def test_news_circuit_breaker_detects_3_star_event():
    breaker = NewsCircuitBreaker(default_buffer_mins=30)
    now = datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc)
    event_time = now + timedelta(minutes=15)

    async with session_factory() as session:
        # Xóa sự kiện cũ nếu có và thêm sự kiện test 3 sao
        await session.execute(delete(EconomicEvent).where(EconomicEvent.title == "TEST Non-Farm Payrolls"))
        event = EconomicEvent(
            source="fair_economy",
            title="TEST Non-Farm Payrolls",
            provider_time_raw="14:15",
            event_timestamp=event_time,
            currency="USD",
            impact_stars=3,
            classification_status="CLASSIFIED",
            timezone_status="VERIFIED",
            revision_no=1,
        )
        session.add(event)
        await session.commit()

        # 1. Kiểm tra trong phạm vi 30 phút
        active, reason, info = await breaker.is_circuit_active(session, target_time=now, buffer_mins=30)
        assert active is True
        assert "TEST Non-Farm Payrolls" in (reason or "")
        assert info is not None
        assert info["impact_stars"] == 3

        # 2. Kiểm tra ngoài phạm vi buffer (ví dụ buffer chỉ 10 phút)
        active_far, _, _ = await breaker.is_circuit_active(session, target_time=now, buffer_mins=10)
        assert active_far is False

        # Cleanup
        await session.execute(delete(EconomicEvent).where(EconomicEvent.title == "TEST Non-Farm Payrolls"))
        await session.commit()


@pytest.mark.anyio
async def test_news_circuit_breaker_ignores_non_3_star_or_non_usd():
    breaker = NewsCircuitBreaker(default_buffer_mins=30)
    now = datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc)
    event_time = now + timedelta(minutes=15)

    async with session_factory() as session:
        await session.execute(delete(EconomicEvent).where(EconomicEvent.title.in_(["TEST EUR PMI", "TEST 2-Star Event"])))
        # Sự kiện 3 sao nhưng là EUR
        e_eur = EconomicEvent(
            source="fair_economy",
            title="TEST EUR PMI",
            provider_time_raw="14:15",
            event_timestamp=event_time,
            currency="EUR",
            impact_stars=3,
            classification_status="CLASSIFIED",
            timezone_status="VERIFIED",
            revision_no=1,
        )
        # Sự kiện USD nhưng chỉ 2 sao
        e_2star = EconomicEvent(
            source="fair_economy",
            title="TEST 2-Star Event",
            provider_time_raw="14:15",
            event_timestamp=event_time,
            currency="USD",
            impact_stars=2,
            classification_status="CLASSIFIED",
            timezone_status="VERIFIED",
            revision_no=1,
        )
        session.add_all([e_eur, e_2star])
        await session.commit()

        active, reason, info = await breaker.is_circuit_active(session, target_time=now, buffer_mins=30)
        assert active is False
        assert reason is None
        assert info is None

        # Cleanup
        await session.execute(delete(EconomicEvent).where(EconomicEvent.title.in_(["TEST EUR PMI", "TEST 2-Star Event"])))
        await session.commit()
