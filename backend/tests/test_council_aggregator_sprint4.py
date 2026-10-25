import httpx
import pytest

from ai_engine.council_aggregator import (
    AgentCouncilState,
    ArbiterPanelState,
    NextEconomicEvent,
    RecentNewsItem,
    ScribeLastTrade,
    ScribePanelState,
    SentinelPanelState,
    SuggestedTradeSetup,
    VectorPanelState,
    council_aggregator,
)
from core.database import session_factory
from main import app


def test_council_aggregator_schemas():
    """Kiểm tra tính hợp lệ và giá trị mặc định của Pydantic Schemas trong Council Aggregator"""
    arbiter = ArbiterPanelState(
        permission="ALLOWED",
        current_risk_percent=1.00,
        sl_multiplier=1.50,
        daily_drawdown_pct=0.45,
        regime_tag="COMPRESSION_CHOP",
        reason_summary="Bình thường",
        hard_breaker_active=False,
    )
    assert arbiter.permission == "ALLOWED"
    assert arbiter.current_risk_percent == 1.00

    sentinel = SentinelPanelState(
        sentiment_score=0.25,
        circuit_breaker_active=False,
        circuit_breaker_status="NORMAL",
        dxy_bias="BEARISH_DXY",
        next_event=NextEconomicEvent(title="USD Core CPI", countdown_seconds=1200, impact_stars=3),
        recent_news=[RecentNewsItem(id="news_1", source="Kitco", title="Gold steady", urgency="MEDIUM", time_ago="5m ago")],
    )
    assert sentinel.sentiment_score == 0.25
    assert sentinel.circuit_breaker_status == "NORMAL"
    assert sentinel.next_event.countdown_seconds == 1200
    assert len(sentinel.recent_news) == 1

    vector = VectorPanelState(
        bias="BULLISH",
        regime="COMPRESSION_CHOP",
        confidence=85,
        rag_similarity=90,
        pattern_match="Wyckoff Spring",
        primary_school="WYCKOFF",
        suggested_trade_setup=SuggestedTradeSetup(
            action="BUY",
            entry_zone=[4128.5, 4132.0],
            suggested_sl=4118.0,
            suggested_tp=4155.0,
            planned_risk_reward=2.2,
        ),
        action_recommendation="Canh mua",
    )
    assert vector.bias == "BULLISH"
    assert vector.suggested_trade_setup.action == "BUY"

    scribe = ScribePanelState(
        last_trade=ScribeLastTrade(
            id=101,
            order_type="BUY",
            realized_pnl=-35.0,
            outcome="LOSS",
            mistake_category="SL_TOO_TIGHT",
            root_cause="Quét thanh khoản",
            lesson_learned="Nới SL",
        ),
        active_memory_rules=["Nới SL phiên London"],
    )
    assert scribe.last_trade.outcome == "LOSS"
    assert scribe.last_trade.mistake_category == "SL_TOO_TIGHT"
    assert len(scribe.active_memory_rules) == 1


@pytest.mark.anyio
async def test_aggregate_council_state_service():
    """Kiểm tra service CouncilAggregator.aggregate_council_state() tổng hợp đủ 4 Agent"""
    async with session_factory() as session:
        state = await council_aggregator.aggregate_council_state(
            session=session, include_test=True, is_test=True
        )

        assert isinstance(state, AgentCouncilState)
        assert state.type == "AGENT_STATE_UPDATE"
        assert state.timestamp > 0

        # Arbiter
        assert state.payload.arbiter.permission in ["ALLOWED", "RESTRICTED", "BLOCKED"]
        assert 0.25 <= state.payload.arbiter.current_risk_percent <= 1.50
        assert 1.00 <= state.payload.arbiter.sl_multiplier <= 3.00

        # Sentinel
        assert -1.00 <= state.payload.sentinel.sentiment_score <= 1.00
        assert state.payload.sentinel.circuit_breaker_status in ["NORMAL", "APPROACHING", "HALT_ACTIVE"]
        assert state.payload.sentinel.dxy_bias in ["BEARISH_DXY", "BULLISH_DXY", "NEUTRAL"]

        # Vector
        assert state.payload.vector.bias in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert 0 <= state.payload.vector.confidence <= 100

        # Scribe
        assert isinstance(state.payload.scribe.active_memory_rules, list)


@pytest.mark.anyio
async def test_get_council_state_direct_api():
    """Kiểm tra gọi trực tiếp endpoint REST API GET /api/v1/agents/council/state"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agents/council/state?include_test=true")
        assert res.status_code == 200

        data = res.json()
        assert data["type"] == "AGENT_STATE_UPDATE"
        assert "arbiter" in data["payload"]
        assert "sentinel" in data["payload"]
        assert "vector" in data["payload"]
        assert "scribe" in data["payload"]

        arbiter = data["payload"]["arbiter"]
        assert arbiter["permission"] in ["ALLOWED", "RESTRICTED", "BLOCKED"]
        assert "current_risk_percent" in arbiter
        assert "sl_multiplier" in arbiter
        assert "daily_drawdown_pct" in arbiter

        sentinel = data["payload"]["sentinel"]
        assert "sentiment_score" in sentinel
        assert "circuit_breaker_status" in sentinel

        vector = data["payload"]["vector"]
        assert "bias" in vector
        assert "confidence" in vector

        scribe = data["payload"]["scribe"]
        assert "active_memory_rules" in scribe


@pytest.mark.anyio
async def test_get_council_state_governor_alias_api():
    """Kiểm tra endpoint alias qua router Governor: GET /api/v1/agents/governor/council/state"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agents/governor/council/state?include_test=true")
        assert res.status_code == 200

        data = res.json()
        assert data["type"] == "AGENT_STATE_UPDATE"
        assert "arbiter" in data["payload"]
        assert "sentinel" in data["payload"]
        assert "vector" in data["payload"]
        assert "scribe" in data["payload"]


@pytest.mark.anyio
async def test_get_council_state_default_api():
    """Kiểm tra gọi trực tiếp endpoint REST API GET /api/v1/agents/council/state không truyền query include_test"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agents/council/state")
        assert res.status_code == 200

        data = res.json()
        assert data["type"] == "AGENT_STATE_UPDATE"
        assert data["payload"]["arbiter"]["permission"] in ["ALLOWED", "RESTRICTED", "BLOCKED"]

