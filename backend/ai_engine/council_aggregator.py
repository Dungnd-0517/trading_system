"""
Council Aggregator Service (Phase 03 - Sprint 04)
Tổng hợp trạng thái toàn diện của 4 Agent AI (Arbiter, Sentinel, Vector, Scribe)
thành một nguồn sự thật duy nhất (Single Source of Truth) phục vụ:
1. REST API hydration: GET /api/v1/agents/council/state
2. WebSocket Hub real-time streaming: Event 'AGENT_STATE_UPDATE' qua Redis channel 'agent:state'
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_agent import news_event_agent
from ai_engine.strategy_governor import strategy_governor
from ai_engine.technical_agent import technical_rag_agent
from core.models import (
    EpisodicTradeMemory,
    FinancialNews,
    SimulatedOrder,
    TradingKnowledge,
)
from core.redis_client import client as redis_client

logger = logging.getLogger(__name__)

REDIS_CHANNEL_AGENT_STATE = "agent:state"
REDIS_KEY_COUNCIL_CACHE = "runtime:agent_council_state"


# ============================================================================
# Pydantic Schemas: Council Deck 4-Agent Specification
# ============================================================================

class ArbiterPanelState(BaseModel):
    permission: str = Field(default="ALLOWED", description="ALLOWED, RESTRICTED, hoặc BLOCKED")
    current_risk_percent: float = Field(default=1.00, ge=0.25, le=1.50)
    sl_multiplier: float = Field(default=1.50, ge=1.00, le=3.00)
    daily_drawdown_pct: float = Field(default=0.00, ge=0.00)
    regime_tag: str = "COMPRESSION_CHOP"
    reason_summary: str = ""
    hard_breaker_active: bool = False


class NextEconomicEvent(BaseModel):
    title: str = ""
    countdown_seconds: int = 0
    impact_stars: int = 3


class RecentNewsItem(BaseModel):
    id: str = ""
    source: str = ""
    title: str = ""
    urgency: str = "MEDIUM"
    time_ago: str = ""


class SentinelPanelState(BaseModel):
    sentiment_score: float = Field(default=0.00, ge=-1.00, le=1.00)
    circuit_breaker_active: bool = False
    circuit_breaker_status: str = "NORMAL"  # "NORMAL", "APPROACHING", "HALT_ACTIVE"
    dxy_bias: str = "NEUTRAL"  # "BEARISH_DXY", "BULLISH_DXY", "NEUTRAL"
    next_event: Optional[NextEconomicEvent] = None
    recent_news: list[RecentNewsItem] = []


class SuggestedTradeSetup(BaseModel):
    action: str = "WAIT"  # "BUY", "SELL", "WAIT"
    entry_zone: list[float] = Field(default_factory=list)
    suggested_sl: float = 0.0
    suggested_tp: float = 0.0
    planned_risk_reward: float = 0.0


class VectorPanelState(BaseModel):
    bias: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    regime: str = "COMPRESSION_CHOP"
    confidence: int = Field(default=50, ge=0, le=100)
    rag_similarity: int = Field(default=0, ge=0, le=100)
    pattern_match: str = ""
    primary_school: str = "GENERAL"
    suggested_trade_setup: Optional[SuggestedTradeSetup] = None
    action_recommendation: str = ""


class ScribeLastTrade(BaseModel):
    id: int
    order_type: str = "BUY"
    realized_pnl: float = 0.0
    outcome: str = "NO_TRADES"  # "WIN", "LOSS", "NO_TRADES"
    mistake_category: Optional[str] = None
    root_cause: Optional[str] = None
    lesson_learned: Optional[str] = None


class ScribePanelState(BaseModel):
    last_trade: Optional[ScribeLastTrade] = None
    active_memory_rules: list[str] = Field(default_factory=list)


class AgentCouncilPayload(BaseModel):
    arbiter: ArbiterPanelState
    sentinel: SentinelPanelState
    vector: VectorPanelState
    scribe: ScribePanelState


class AgentCouncilState(BaseModel):
    type: str = "AGENT_STATE_UPDATE"
    timestamp: int
    payload: AgentCouncilPayload


# ============================================================================
# Council Aggregator Engine
# ============================================================================

class CouncilAggregator:
    """
    Điều phối và tổng hợp trạng thái thời gian thực từ 4 Agent cốt lõi:
    - Arbiter: Tham số rủi ro, SL, Drawdown và trạng thái Hard Guardrails.
    - Sentinel: Cảm xúc vĩ mô, Circuit Breaker, tin tức nóng và đếm ngược sự kiện đỏ USD.
    - Vector: Phân tích cấu trúc nến M15, Regime, RAG Pattern Match và Trade Setup.
    - Scribe: Lệnh đóng gần nhất, phân loại lỗi post-mortem và danh sách Active Rules.
    """

    async def aggregate_council_state(
        self,
        session: AsyncSession,
        include_test: bool = False,
        is_test: bool = False,
    ) -> AgentCouncilState:
        now = datetime.now(timezone.utc)
        include_flag = include_test or is_test

        # --------------------------------------------------------------------
        # 1. ARBITER (Strategy Governor & Risk Guardian)
        # --------------------------------------------------------------------
        params = await strategy_governor.get_current_runtime_params()
        daily_dd = await strategy_governor.calculate_daily_drawdown(
            session=session, include_test=include_flag
        )
        regime, _ = await strategy_governor.evaluate_market_regime(session)

        hard_breaker_active = daily_dd >= 3.0
        risk_pct = float(params.get("risk_per_trade_percent", 1.0))
        sl_mult = float(params.get("atr_sl_multiplier", 1.5))
        is_trading_allowed = bool(params.get("trading_allowed", True))

        if hard_breaker_active:
            permission = "BLOCKED"
            reason = f"HARD_LIMIT_BREACHED: Max daily drawdown 3% reached ({daily_dd:.2f}%)."
        elif not is_trading_allowed:
            permission = "BLOCKED"
            reason = str(params.get("halt_reason") or "Giao dịch đang tạm dừng bởi Trader hoặc Governor.")
        elif risk_pct < 0.50 or regime == "HIGH_VOLATILITY":
            permission = "RESTRICTED"
            reason = f"Thị trường {regime}. Áp dụng chế độ siết chặt rủi ro {risk_pct:.2f}%."
        else:
            permission = "ALLOWED"
            reason = str(params.get("halt_reason") or f"Thị trường {regime}. Cho phép mở lệnh với rủi ro {risk_pct:.2f}%.")

        arbiter_state = ArbiterPanelState(
            permission=permission,
            current_risk_percent=risk_pct,
            sl_multiplier=sl_mult,
            daily_drawdown_pct=daily_dd,
            regime_tag=regime,
            reason_summary=reason,
            hard_breaker_active=hard_breaker_active,
        )

        # --------------------------------------------------------------------
        # 2. SENTINEL (News & Macro Watchdog)
        # --------------------------------------------------------------------
        macro_report = await news_event_agent.generate_macro_report(
            session=session, target_time=now, broadcast=False
        )
        circuit_status = "NORMAL"
        if macro_report.circuit_breaker_details:
            circuit_status = macro_report.circuit_breaker_details.status
        elif macro_report.active_circuit_breaker:
            circuit_status = "HALT_ACTIVE"

        next_ev = None
        if macro_report.high_impact_events_upcoming:
            ev = macro_report.high_impact_events_upcoming[0]
            next_ev = NextEconomicEvent(
                title=str(ev.get("name") or ev.get("title") or "USD High Impact Event"),
                countdown_seconds=max(0, int(ev.get("countdown_seconds", 0))),
                impact_stars=int(ev.get("impact_stars", 3)),
            )

        # Trích xuất tin tức nóng gần nhất
        news_stmt = select(FinancialNews).order_by(FinancialNews.published_at.desc()).limit(3)
        recent_news_records = (await session.execute(news_stmt)).scalars().all()

        recent_news_items: list[RecentNewsItem] = []
        for n in recent_news_records:
            mins_ago = max(1, int((now - n.published_at).total_seconds() // 60))
            time_ago_str = f"{mins_ago}m ago" if mins_ago < 60 else f"{mins_ago // 60}h ago"
            urgency = "CRITICAL" if (n.impact_stars == 3 or str(n.impact_level).upper() in ["HIGH", "CRITICAL"]) else ("HIGH" if n.impact_stars == 2 else "MEDIUM")
            recent_news_items.append(
                RecentNewsItem(
                    id=f"news_{n.id}",
                    source=n.source or "Financial News",
                    title=n.title,
                    urgency=urgency,
                    time_ago=time_ago_str,
                )
            )

        sentinel_state = SentinelPanelState(
            sentiment_score=round(macro_report.macro_sentiment_score, 2),
            circuit_breaker_active=macro_report.active_circuit_breaker,
            circuit_breaker_status=circuit_status,
            dxy_bias=macro_report.dxy_correlation_bias or "NEUTRAL",
            next_event=next_ev,
            recent_news=recent_news_items,
        )

        # --------------------------------------------------------------------
        # 3. VECTOR (Technical RAG Specialist)
        # --------------------------------------------------------------------
        tech_report = await technical_rag_agent.generate_technical_analysis(
            session=session, symbol="XAUUSD", timeframe="M15"
        )
        pattern_match = ""
        rag_sim = 0
        if tech_report.retrieved_knowledge_chunks:
            top_chunk = tech_report.retrieved_knowledge_chunks[0]
            pattern_match = top_chunk.title
            rag_sim = int(round(top_chunk.similarity_score * 100))

        trade_setup = None
        if tech_report.suggested_trade_setup:
            ts = tech_report.suggested_trade_setup
            trade_setup = SuggestedTradeSetup(
                action=ts.action,
                entry_zone=[float(x) for x in ts.entry_zone],
                suggested_sl=float(ts.suggested_sl),
                suggested_tp=float(ts.suggested_tp),
                planned_risk_reward=float(ts.planned_risk_reward),
            )

        action_rec = (
            tech_report.notes[0]
            if tech_report.notes
            else f"Ưu tiên theo dõi xu hướng {tech_report.structural_bias} tại khung nến M15."
        )

        vector_state = VectorPanelState(
            bias=tech_report.structural_bias,
            regime=tech_report.market_regime,
            confidence=int(round(tech_report.confidence_score * 100)),
            rag_similarity=rag_sim,
            pattern_match=pattern_match,
            primary_school=tech_report.primary_school,
            suggested_trade_setup=trade_setup,
            action_recommendation=action_rec,
        )

        # --------------------------------------------------------------------
        # 4. SCRIBE (Reflexion Learning Coach)
        # --------------------------------------------------------------------
        mem_stmt = select(EpisodicTradeMemory).order_by(EpisodicTradeMemory.created_at.desc()).limit(1)
        if not include_flag:
            mem_stmt = mem_stmt.where(EpisodicTradeMemory.is_test.is_(False))
        last_mem = (await session.execute(mem_stmt)).scalar_one_or_none()

        last_trade = None
        if last_mem:
            order_type = "BUY"
            realized_pnl = 0.0
            if last_mem.order_id:
                order = await session.get(SimulatedOrder, last_mem.order_id)
                if order:
                    order_type = order.order_type
                    realized_pnl = float(order.realized_pnl or 0.0)

            last_trade = ScribeLastTrade(
                id=last_mem.order_id or last_mem.id,
                order_type=order_type,
                realized_pnl=realized_pnl,
                outcome=last_mem.outcome or "NO_TRADES",
                mistake_category=last_mem.mistake_category,
                root_cause=last_mem.root_cause,
                lesson_learned=last_mem.lesson_learned,
            )

        # Lấy danh sách quy tắc đang áp dụng từ TradingKnowledge hoặc EpisodicTradeMemory
        rule_stmt = (
            select(TradingKnowledge.title, TradingKnowledge.content)
            .where(TradingKnowledge.source_type == "REFLEXION_PROMOTED")
            .order_by(TradingKnowledge.created_at.desc())
            .limit(5)
        )
        if not include_flag:
            rule_stmt = rule_stmt.where(TradingKnowledge.is_test.is_(False))
        promoted_rules = (await session.execute(rule_stmt)).all()

        active_memory_rules = [
            f"{r[0]}: {r[1]}" if r[0] != r[1] else r[0] for r in promoted_rules
        ]
        if not active_memory_rules:
            # Fallback sang các quy tắc rút ra gần nhất trong bộ nhớ
            fallback_stmt = (
                select(EpisodicTradeMemory.rule_to_add)
                .where(EpisodicTradeMemory.rule_to_add.is_not(None))
                .order_by(EpisodicTradeMemory.created_at.desc())
                .limit(3)
            )
            if not include_flag:
                fallback_stmt = fallback_stmt.where(EpisodicTradeMemory.is_test.is_(False))
            fb_rules = (await session.execute(fallback_stmt)).scalars().all()
            active_memory_rules = [r for r in fb_rules if r]

        scribe_state = ScribePanelState(
            last_trade=last_trade,
            active_memory_rules=active_memory_rules,
        )

        # --------------------------------------------------------------------
        # 5. ASSEMBLE FULL COUNCIL STATE
        # --------------------------------------------------------------------
        payload = AgentCouncilPayload(
            arbiter=arbiter_state,
            sentinel=sentinel_state,
            vector=vector_state,
            scribe=scribe_state,
        )

        state = AgentCouncilState(
            type="AGENT_STATE_UPDATE",
            timestamp=int(now.timestamp()),
            payload=payload,
        )

        # Lưu cache nhanh vào Redis để truy xuất nhanh
        try:
            await redis_client.set(
                REDIS_KEY_COUNCIL_CACHE,
                state.model_dump_json(),
                ex=30,  # TTL 30s
            )
        except Exception as e:
            logger.debug(f"Redis cache council state skipped: {e}")

        return state

    async def broadcast_council_state(self, state: AgentCouncilState) -> None:
        """Phát sóng gói trạng thái cập nhật qua kênh Redis Pub/Sub chuẩn 'agent:state'"""
        try:
            message_json = state.model_dump_json()
            await redis_client.publish(REDIS_CHANNEL_AGENT_STATE, message_json)
        except Exception as exc:
            logger.warning(f"Lỗi khi phát sóng council state qua Redis: {exc}")

    async def trigger_and_broadcast_council_state(
        self,
        session: Optional[AsyncSession] = None,
        include_test: bool = False,
        is_test: bool = False,
    ) -> AgentCouncilState:
        """
        Tiện ích tổng hợp trạng thái mới nhất của 4 Agent và phát sóng tức thì qua Redis channel 'agent:state'.
        Nếu không truyền session, tự động mở một session ngắn từ session_factory.
        """
        if session is not None:
            state = await self.aggregate_council_state(
                session=session, include_test=include_test, is_test=is_test
            )
            await self.broadcast_council_state(state)
            return state

        from core.database import session_factory
        async with session_factory() as s:
            state = await self.aggregate_council_state(
                session=s, include_test=include_test, is_test=is_test
            )
            await self.broadcast_council_state(state)
            return state


# Singleton instance
council_aggregator = CouncilAggregator()

