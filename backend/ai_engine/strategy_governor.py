import asyncio
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import json
import logging
import re
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_agent import news_event_agent
from ai_engine.news_guard import news_circuit_breaker
from ai_engine.reflexion_service import reflexion_service
from ai_engine.technical_agent import technical_rag_agent
from core.database import session_factory
from core.models import (
    AgentDecisionLog,
    AgentTraderDialogue,
    EpisodicTradeMemory,
    FinancialNews,
    MarketCandle,
    SimulatedOrder,
    SimulationAccount,
    SystemTradingConfig,
)
from core.redis_client import redis_client

logger = logging.getLogger(__name__)

REDIS_RUNTIME_PARAMS_KEY = "runtime:params:XAUUSD"


class AgentParamAdjustment(BaseModel):
    risk_per_trade_percent: float = Field(default=1.00, ge=0.25, le=1.50)
    min_risk_reward_ratio: float = Field(default=1.50, ge=1.20, le=4.00)
    atr_sl_multiplier: float = Field(default=1.50, ge=1.00, le=3.00)
    trading_allowed: bool = True
    halt_reason: Optional[str] = None
    updated_by_agent: str = "STRATEGY_GOVERNOR"


class ConsensusReport(BaseModel):
    timestamp: str
    market_regime: str
    suggested_bias: str
    confidence_score: float
    news_sentiment_score: float
    has_active_news_halt: bool
    recent_loss_count: int
    top_mistake_patterns: list[str]
    current_daily_drawdown_pct: float
    active_params: AgentParamAdjustment
    rationale: str


class ExecutiveBriefingResponse(BaseModel):
    dialogue_id: Optional[int] = None
    timestamp: str
    headline: str
    macro_summary: str
    technical_summary: str
    reflexion_summary: str
    risk_mandate_summary: str
    active_params: AgentParamAdjustment
    briefing_text: str


class TraderDialogueResponse(BaseModel):
    trader_message_id: int
    governor_message_id: int
    response: str
    actions_taken: dict[str, Any]
    guardrail_passed: bool
    active_params: AgentParamAdjustment


def validate_and_apply_hard_guardrails(
    proposed_params: dict[str, Any],
    current_daily_drawdown: float,
) -> tuple[AgentParamAdjustment, bool]:
    """
    BỘ RÀO CHẮN CỨNG (Hard Constraints Guardrails viết bằng Python thuần):
    1. Rào chắn 1: Nếu tổng lỗ trong ngày >= 3.0%, KHÓA CỨNG quyền giao dịch bất kể AI đề xuất gì.
    2. Rào chắn 2: Ép kiểu và kiểm tra biên độ an toàn tuyệt đối qua Pydantic:
       - risk_per_trade_percent: [0.25%, 1.50%]
       - min_risk_reward_ratio: [1.20, 4.00]
       - atr_sl_multiplier: [1.00, 3.00]
    """
    was_overridden = False

    # RÀO CHẮN 1: Max daily drawdown 3%
    if current_daily_drawdown >= 3.0:
        proposed_params["trading_allowed"] = False
        proposed_params["halt_reason"] = (
            f"HARD_LIMIT_BREACHED: Max daily drawdown 3% reached ({current_daily_drawdown:.2f}%)."
        )
        was_overridden = True

    # Kẹp giá trị (Clamp) vào dải an toàn trước khi ném vào Pydantic để tránh crash
    risk = float(proposed_params.get("risk_per_trade_percent", 1.0))
    risk_clamped = max(0.25, min(1.50, round(risk, 2)))

    rr = float(proposed_params.get("min_risk_reward_ratio", 1.50))
    rr_clamped = max(1.20, min(4.00, round(rr, 2)))

    atr_mult = float(proposed_params.get("atr_sl_multiplier", 1.50))
    atr_mult_clamped = max(1.00, min(3.00, round(atr_mult, 2)))

    validated = AgentParamAdjustment(
        risk_per_trade_percent=risk_clamped,
        min_risk_reward_ratio=rr_clamped,
        atr_sl_multiplier=atr_mult_clamped,
        trading_allowed=bool(proposed_params.get("trading_allowed", True)),
        halt_reason=proposed_params.get("halt_reason"),
        updated_by_agent=str(proposed_params.get("updated_by_agent", "STRATEGY_GOVERNOR")),
    )

    return validated, was_overridden


class StrategyGovernor:
    """
    Trưởng ban Quản trị Rủi ro (CRO - Chief Risk Officer):
    - Tổng hợp nhận định từ 3 Agent (News, Technical RAG, Reflexion).
    - Tính toán Drawdown ngày và tần suất lỗi gần nhất.
    - Áp dụng Hard Guardrails và đồng bộ tham số vào system_trading_config + Redis Cache.
    """

    async def calculate_daily_drawdown(
        self, session: AsyncSession, include_test: bool = False
    ) -> float:
        """Tính toán tỷ lệ sụt giảm tài khoản trong ngày hiện tại (%)"""
        now = datetime.now(timezone.utc)
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

        # 1. Tổng PnL thực nhận các lệnh đã đóng hôm nay
        pnl_stmt = (
            select(func.sum(SimulatedOrder.realized_pnl))
            .where(
                SimulatedOrder.status == "CLOSED",
                SimulatedOrder.close_time >= start_of_day,
            )
        )
        if not include_test:
            pnl_stmt = pnl_stmt.where(SimulatedOrder.is_test.is_(False))

        today_pnl = (await session.execute(pnl_stmt)).scalar() or Decimal("0.0")

        # 2. Lấy số dư ban đầu từ tài khoản mô phỏng
        acc = await session.get(SimulationAccount, 1)
        initial_balance = float(acc.initial_balance) if acc else 10000.0

        # Nếu lỗ, tính % drawdown (giá trị dương)
        today_loss = max(0.0, -float(today_pnl))
        drawdown_pct = (today_loss / initial_balance) * 100.0
        return round(drawdown_pct, 2)

    async def evaluate_market_regime(
        self, session: AsyncSession, symbol: str = "XAUUSD"
    ) -> tuple[str, float]:
        """Đánh giá trạng thái biến động thị trường (Regime) và ATR(14) trên khung M15"""
        candle_stmt = (
            select(MarketCandle)
            .where(MarketCandle.symbol == symbol, MarketCandle.timeframe == "M15")
            .order_by(MarketCandle.open_time.desc())
            .limit(20)
        )
        candles = (await session.execute(candle_stmt)).scalars().all()
        if len(candles) < 14:
            return "NORMAL", 20.0  # Baseline mặc định cho Vàng

        # Tính True Range (TR)
        highs = [float(c.high) for c in reversed(candles)]
        lows = [float(c.low) for c in reversed(candles)]
        closes = [float(c.close) for c in reversed(candles)]

        trs = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)

        atr_val = float(np.mean(trs[-14:])) if trs else 20.0

        # Phân loại Regime dựa trên ngưỡng ATR của Vàng
        # ATR thông thường: 15 - 25 points. ATR cao: > 35 points
        if atr_val > 35.0:
            regime = "HIGH_VOLATILITY"
        elif atr_val < 15.0:
            regime = "COMPRESSION_CHOP"
        else:
            regime = "TRENDING"

        return regime, round(atr_val, 2)

    async def review_recent_reflexions(
        self, session: AsyncSession, include_test: bool = False
    ) -> tuple[int, list[str]]:
        """Rà soát các bài học gần nhất từ Reflexion Engine (10 lệnh gần nhất)"""
        mem_stmt = select(EpisodicTradeMemory).order_by(
            EpisodicTradeMemory.created_at.desc()
        ).limit(10)
        if not include_test:
            mem_stmt = mem_stmt.where(EpisodicTradeMemory.is_test.is_(False))

        records = (await session.execute(mem_stmt)).scalars().all()

        recent_losses = sum(1 for m in records if m.outcome == "LOSS")
        mistakes = [m.mistake_category for m in records if m.mistake_category]

        return recent_losses, mistakes

    async def synthesize_consensus(
        self,
        session: AsyncSession,
        include_test: bool = False,
        is_test: bool = False,
    ) -> ConsensusReport:
        """
        Tổng hợp đồng thuận (Consensus) từ 3 Agent và áp dụng Hard Guardrails:
        - News Agent: Sentiment và Circuit Breaker.
        - Technical RAG: Volatility regime và ATR.
        - Reflexion Agent: Các lỗi sai lầm gần nhất.
        """
        now = datetime.now(timezone.utc)

        # 1. Thu thập dữ liệu News Agent từ NewsEventAgent
        macro_report = await news_event_agent.generate_macro_report(
            session=session, target_time=now, broadcast=False
        )
        is_news_halt = macro_report.active_circuit_breaker
        news_reason = macro_report.recommendation_for_governor.reason
        sentiment_score = macro_report.macro_sentiment_score

        # 2. Thu thập dữ liệu Technical Agent từ TechnicalRagAgent
        tech_report = await technical_rag_agent.generate_technical_analysis(session=session)
        regime, current_atr = await self.evaluate_market_regime(session)

        # 3. Thu thập dữ liệu Reflexion Agent
        recent_losses, mistake_patterns = await self.review_recent_reflexions(
            session, include_test=include_test or is_test
        )

        # 4. Tính toán Daily Drawdown
        daily_dd = await self.calculate_daily_drawdown(
            session, include_test=include_test or is_test
        )

        # 5. Logic đề xuất thích ứng của Governor
        suggested_risk = 1.00
        suggested_atr_multiplier = 1.50
        suggested_rr = 1.50
        trading_allowed = True
        halt_reason = None
        bias = "NEUTRAL"
        confidence = 0.80
        if tech_report and tech_report.confidence_score:
            confidence = round((confidence + tech_report.confidence_score) / 2, 2)
        reasons: list[str] = []

        # Tác động từ News
        if is_news_halt:
            trading_allowed = False
            halt_reason = f"NEWS_CIRCUIT_BREAKER_ACTIVE: {news_reason}"
            reasons.append("News circuit breaker active around 3-star event")
        elif sentiment_score >= 0.35:
            bias = "LONG_ONLY"
            reasons.append(f"Bullish news sentiment (+{sentiment_score:.2f})")
        elif sentiment_score <= -0.35:
            bias = "SHORT_ONLY"
            reasons.append(f"Bearish news sentiment ({sentiment_score:.2f})")

        # Tác động từ Technical Regime
        if regime == "HIGH_VOLATILITY":
            suggested_risk = 0.50  # Hạ một nửa khối lượng khi biến động quá lớn
            suggested_atr_multiplier = 2.00  # Nới rộng SL để tránh bị quét râu
            reasons.append(f"Elevated ATR ({current_atr:.1f} pts) -> Halved risk, widened SL to 2.0x")
        elif regime == "COMPRESSION_CHOP":
            suggested_rr = 1.80  # Đòi hỏi RR cao hơn khi thị trường nén
            reasons.append(f"Low volatility compression ({current_atr:.1f} pts)")

        # Tác động từ Reflexion Memory Feedback Loop
        sl_tight_count = mistake_patterns.count("SL_TOO_TIGHT")
        if sl_tight_count >= 2:
            suggested_atr_multiplier = max(suggested_atr_multiplier, 1.80)
            reasons.append(
                f"Reflexion alert: {sl_tight_count} recent SL_TOO_TIGHT -> Enforced ATR multiplier >= 1.80x"
            )

        early_entry_count = mistake_patterns.count("EARLY_ENTRY")
        if early_entry_count >= 2:
            suggested_rr = max(suggested_rr, 1.80)
            reasons.append(f"Reflexion alert: {early_entry_count} recent EARLY_ENTRY -> Requiring minimum 1:1.80 R:R")

        if recent_losses >= 3:
            suggested_risk = min(suggested_risk, 0.50)  # Throttling rủi ro khi dính chuỗi 3 lệnh thua
            reasons.append("3 consecutive losses -> Throttled risk to 0.50%")

        # 6. Đóng vòng lặp qua BỘ RÀO CHẮN CỨNG (Hard Constraints Guardrails)
        proposed_dict = {
            "risk_per_trade_percent": suggested_risk,
            "min_risk_reward_ratio": suggested_rr,
            "atr_sl_multiplier": suggested_atr_multiplier,
            "trading_allowed": trading_allowed,
            "halt_reason": halt_reason,
            "updated_by_agent": "STRATEGY_GOVERNOR",
        }

        validated_params, was_hard_breached = validate_and_apply_hard_guardrails(
            proposed_dict, current_daily_drawdown=daily_dd
        )
        if was_hard_breached:
            reasons.append(f"Hard constraint locked: Max daily drawdown reached ({daily_dd:.2f}%)")

        rationale_str = "; ".join(reasons) if reasons else "Standard operational parameters maintained."

        report = ConsensusReport(
            timestamp=now.isoformat(),
            market_regime=regime,
            suggested_bias=bias,
            confidence_score=confidence,
            news_sentiment_score=round(sentiment_score, 2),
            has_active_news_halt=is_news_halt,
            recent_loss_count=recent_losses,
            top_mistake_patterns=list(set(mistake_patterns)),
            current_daily_drawdown_pct=daily_dd,
            active_params=validated_params,
            rationale=rationale_str,
        )

        # 6b. Ghi nhận AgentDecisionLog vào PostgreSQL
        decision_log = AgentDecisionLog(
            market_regime=regime,
            suggested_bias=bias,
            consensus_score=Decimal(f"{confidence:.2f}"),
            technical_confidence=Decimal(f"{(tech_report.confidence_score if tech_report else 0.80):.2f}"),
            macro_sentiment_score=Decimal(f"{sentiment_score:.2f}"),
            active_circuit_breaker=is_news_halt,
            applied_risk_pct=Decimal(f"{validated_params.risk_per_trade_percent:.2f}"),
            applied_sl_mult=Decimal(f"{validated_params.atr_sl_multiplier:.2f}"),
            applied_min_rr=Decimal(f"{validated_params.min_risk_reward_ratio:.2f}"),
            trading_allowed=validated_params.trading_allowed,
            halt_reason=validated_params.halt_reason,
            rationale_summary=rationale_str,
            agent_votes={
                "news": {
                    "sentiment": sentiment_score,
                    "circuit_breaker": is_news_halt,
                    "bias": macro_report.macro_bias if macro_report else "NEUTRAL",
                },
                "technical": {
                    "regime": regime,
                    "atr": current_atr,
                    "confidence": tech_report.confidence_score if tech_report else 0.80,
                },
                "reflexion": {
                    "recent_losses": recent_losses,
                    "mistakes": mistake_patterns,
                },
            },
            is_test=include_test or is_test,
        )
        session.add(decision_log)

        # 7. Đồng bộ hóa 2 tầng: PostgreSQL (system_trading_config) & Redis Cache
        await self._persist_and_sync_cache(session, validated_params)
        return report

    async def _persist_and_sync_cache(
        self, session: AsyncSession, params: AgentParamAdjustment
    ) -> None:
        """Cập nhật database system_trading_config và sync sang Redis cache"""
        now = datetime.now(timezone.utc)
        cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
        if not cfg:
            cfg = SystemTradingConfig(id=1)
            session.add(cfg)

        cfg.risk_per_trade_percent = Decimal(f"{params.risk_per_trade_percent:.2f}")
        cfg.min_risk_reward_ratio = Decimal(f"{params.min_risk_reward_ratio:.2f}")
        cfg.atr_sl_multiplier = Decimal(f"{params.atr_sl_multiplier:.2f}")
        cfg.trading_allowed = params.trading_allowed
        cfg.halt_reason = params.halt_reason
        cfg.updated_by_agent = params.updated_by_agent
        cfg.updated_at = now
        await session.commit()

        # Cache vào Redis
        try:
            payload = params.model_dump_json()
            await redis_client.set(REDIS_RUNTIME_PARAMS_KEY, payload)
            await redis_client.publish(
                "governor:consensus",
                json.dumps(
                    {
                        "type": "governor.update",
                        "data": params.model_dump(),
                        "timestamp": now.isoformat(),
                    }
                ),
            )
        except Exception as exc:
            logger.warning("Failed to sync runtime params to Redis: %s", exc)

    async def get_current_runtime_params(self) -> dict[str, Any]:
        """Đọc bộ tham số hiện tại (ưu tiên Redis, fallback DB)"""
        try:
            cached = await redis_client.get(REDIS_RUNTIME_PARAMS_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        async with session_factory() as session:
            cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
            if cfg:
                return {
                    "risk_per_trade_percent": float(cfg.risk_per_trade_percent),
                    "min_risk_reward_ratio": float(cfg.min_risk_reward_ratio),
                    "atr_sl_multiplier": float(cfg.atr_sl_multiplier),
                    "trading_allowed": cfg.trading_allowed,
                    "halt_reason": cfg.halt_reason,
                    "updated_by_agent": cfg.updated_by_agent,
                }

        return AgentParamAdjustment().model_dump()

    async def generate_executive_briefing(
        self, session: AsyncSession, include_test: bool = False, is_test: bool = False
    ) -> dict[str, Any]:
        """
        Xuất bản bản tin điều hành tóm tắt vĩ mô, cấu trúc kỹ thuật, bài học reflexion và rủi ro.
        Lưu vào bảng agent_trader_dialogue và trả về cấu trúc chi tiết.
        """
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Thu thập dữ liệu News Agent
        macro_report = await news_event_agent.generate_macro_report(
            session=session, target_time=now, broadcast=False
        )
        cb_status = "ĐANG KÍCH HOẠT (HALT_ACTIVE)" if macro_report.active_circuit_breaker else "BÌNH THƯỜNG (NORMAL)"
        sentiment_score = macro_report.macro_sentiment_score
        macro_bias = macro_report.macro_bias
        cb_reason = (
            macro_report.recommendation_for_governor.reason
            if macro_report.active_circuit_breaker
            else "Không có sự kiện 3 sao trong phạm vi 30 phút."
        )

        # 2. Thu thập dữ liệu Technical Agent
        tech_report = await technical_rag_agent.generate_technical_analysis(session=session)
        regime, current_atr = await self.evaluate_market_regime(session)
        tech_bias = tech_report.structural_bias if tech_report else "NEUTRAL"
        tech_conf = int((tech_report.confidence_score if tech_report else 0.80) * 100)

        # 3. Thu thập dữ liệu Reflexion
        recent_losses, mistake_patterns = await self.review_recent_reflexions(
            session, include_test=include_test or is_test
        )
        mistake_str = ", ".join(set(mistake_patterns)) if mistake_patterns else "Không có mẫu hình lỗi lặp lại gần đây"

        # 4. Sụt giảm và Tham số vận hành hiện tại
        daily_dd = await self.calculate_daily_drawdown(
            session, include_test=include_test or is_test
        )
        params = await self.get_current_runtime_params()
        allowed_str = (
            "CHO PHÉP MỞ LỆNH"
            if params.get("trading_allowed", True)
            else f"TẠM KHÓA GIAO DỊCH ({params.get('halt_reason', 'N/A')})"
        )

        # 5. Xây dựng nội dung bản tin (Briefing Text Markdown)
        briefing_text = (
            f"🏛️ **BẢN TIN ĐIỀU HÀNH CHIẾN LƯỢC (EXECUTIVE BRIEFING)**\n"
            f"⏱️ *Thời gian phát hành:* {now_str} | *Chỉ huy:* Strategy Governor (CRO)\n\n"
            f"**1. Bối cảnh Vĩ mô & Sự kiện (News & Event Agent):**\n"
            f"- Điểm cảm xúc vĩ mô: **{sentiment_score:+.2f}** ({macro_bias})\n"
            f"- Trạng thái Circuit Breaker: **{cb_status}**\n"
            f"- Chi tiết: {cb_reason}\n\n"
            f"**2. Cấu trúc Kỹ thuật Đa Trường phái (Technical RAG Agent):**\n"
            f"- Trạng thái biến động (Regime): **{regime}** (ATR M15: {current_atr:.1f} pts)\n"
            f"- Thiên hướng kỹ thuật: **{tech_bias}** (Độ tin cậy: {tech_conf}%)\n"
            f"- Hợp lưu: Wyckoff, ICT, CMT, SMC & Traps đang duy trì cấu trúc nhất quán.\n\n"
            f"**3. Phản tư & Phòng ngừa Sai lầm (Reflexion Agent):**\n"
            f"- Tỷ lệ lệnh thua gần đây: **{recent_losses}/10 lệnh**\n"
            f"- Nhóm sai lầm cảnh báo: **{mistake_str}**\n\n"
            f"**4. Chỉ thị Quản trị Rủi ro Hiện hành (Governor Mandate):**\n"
            f"- Trạng thái: **{allowed_str}**\n"
            f"- Rủi ro áp dụng: **{params.get('risk_per_trade_percent', 1.0):.2f}%** / lệnh (Biên an toàn [0.25%, 1.50%])\n"
            f"- ATR SL Multiplier: **{params.get('atr_sl_multiplier', 1.5):.2f}x**\n"
            f"- Tỷ lệ R:R tối thiểu: **1:{params.get('min_risk_reward_ratio', 1.5):.2f}**\n"
            f"- Sụt giảm trong ngày (Drawdown): **{daily_dd:.2f}%** / tối đa 3.00%"
        )

        headline = f"Executive Briefing {now_str}: {regime} | Risk {params.get('risk_per_trade_percent', 1.0):.2f}% | DD {daily_dd:.2f}%"

        # 6. Ghi bản ghi vào agent_trader_dialogue
        dialogue = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="BRIEFING",
            content=briefing_text,
            metadata_={
                "headline": headline,
                "macro_score": sentiment_score,
                "market_regime": regime,
                "atr": current_atr,
                "recent_losses": recent_losses,
                "daily_drawdown_pct": daily_dd,
                "active_params": params,
            },
            approval_status=None,
            is_test=include_test or is_test,
        )
        session.add(dialogue)
        await session.commit()
        await session.refresh(dialogue)

        # Phát sóng Redis event
        try:
            await redis_client.publish(
                "agent:trader:dialogue",
                json.dumps({
                    "type": "agent.dialogue.message",
                    "dialogue": {
                        "id": dialogue.id,
                        "sender": dialogue.sender,
                        "message_type": dialogue.message_type,
                        "content": dialogue.content,
                        "timestamp": dialogue.timestamp.isoformat(),
                    },
                }),
            )
        except Exception as e:
            logger.warning("Failed to publish briefing to Redis: %s", e)

        return {
            "dialogue_id": dialogue.id,
            "timestamp": now.isoformat(),
            "headline": headline,
            "macro_summary": f"Điểm cảm xúc: {sentiment_score:+.2f} ({macro_bias}), Circuit Breaker: {cb_status}",
            "technical_summary": f"Regime: {regime}, ATR: {current_atr:.1f} pts, Bias: {tech_bias} ({tech_conf}%)",
            "reflexion_summary": f"Lỗ gần đây: {recent_losses}/10, Cảnh báo: {mistake_str}",
            "risk_mandate_summary": f"Trạng thái: {allowed_str}, Risk: {params.get('risk_per_trade_percent')}%, SL: {params.get('atr_sl_multiplier')}x, DD: {daily_dd:.2f}%",
            "active_params": params,
            "briefing_text": briefing_text,
        }

    async def process_trader_dialogue(
        self,
        message: str,
        session: AsyncSession,
        is_test: bool = False,
        conversation_id: int | None = None,
        client_msg_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Kênh đối thoại hai chiều Trader - Governor:
        - Nhận thông điệp / câu lệnh từ Trader.
        - Trích xuất ý định (Intent Parsing) cho các thao tác ghi đè (rủi ro, sl, dừng/mở giao dịch, briefing).
        - Thẩm định qua Bộ Rào chắn Cứng (Hard Guardrails D21/D24).
        - Từ chối dứt khoát và giải thích nguyên tắc bảo toàn vốn nếu vi phạm.
        - Ghi nhật ký vào agent_trader_dialogue và đồng bộ Single Source of Truth.
        """
        message_clean = message.strip()
        lower_msg = message_clean.lower()

        # 1. Intent Parsing
        # Nhận diện lệnh Briefing
        is_briefing_request = any(
            k in lower_msg
            for k in [
                "báo cáo điều hành",
                "executive briefing",
                "tóm tắt tình hình",
                "báo cáo thị trường",
                "tình hình hôm nay",
                "báo cáo tổng quan",
                "briefing",
            ]
        )

        # Nhận diện lệnh Rủi ro (Risk %)
        # Ví dụ: "Hạ mức rủi ro xuống 0.5%", "set risk to 0.75%", "rủi ro 5%", "risk 1.2%"
        risk_match = re.search(
            r"(?:hạ|giảm|tăng|đặt|set|mức|chỉnh)?\s*(?:rủi\s*ro|risk)[\s\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ:=]*?([0-9]+(?:\.[0-9]+)?)\s*%",
            lower_msg,
        )
        if not risk_match:
            risk_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:rủi\s*ro|risk)", lower_msg)
        if not risk_match:
            risk_match = re.search(r"(?:rủi\s*ro|risk)[\s:=]+([0-9]+(?:\.[0-9]+)?)", lower_msg)

        # Nhận diện lệnh ATR SL Multiplier
        # Ví dụ: "Nới SL lên 2.2x ATR", "Nới SL lên 2.0", "sl 2.5x", "atr 2.0"
        atr_match = re.search(
            r"(?:nới|hạ|đặt|tăng|giảm|set)?\s*(?:sl|atr|stop\s*loss|cắt\s*lỗ)[\s\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ:=]*?([0-9]+(?:\.[0-9]+)?)\s*(?:x|lần)?(?:\s*atr)?",
            lower_msg,
        )

        # Nhận diện lệnh Min Risk:Reward
        rr_match = re.search(
            r"(?:tỷ\s*lệ|min)?\s*(?:rr|r:r|risk\s*reward)[\s\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ:=]*?([0-9]+(?:\.[0-9]+)?)",
            lower_msg,
        )

        # Nhận diện lệnh Tạm dừng / Tiếp tục
        is_pause = any(
            k in lower_msg
            for k in [
                "tạm dừng",
                "dừng giao dịch",
                "ngừng giao dịch",
                "khóa lệnh",
                "pause",
                "halt",
                "ngắt giao dịch",
            ]
        )
        is_resume = any(
            k in lower_msg
            for k in [
                "tiếp tục",
                "mở lại giao dịch",
                "bật giao dịch",
                "kích hoạt lại",
                "resume",
                "unpause",
                "mở khóa",
            ]
        )

        # 2. Lưu tin nhắn của Trader vào agent_trader_dialogue
        is_command = bool(risk_match or atr_match or rr_match or is_pause or is_resume or is_briefing_request)
        trader_msg = AgentTraderDialogue(
            conversation_id=conversation_id,
            client_msg_id=client_msg_id,
            target_agent="GOVERNOR",
            sender="TRADER",
            message_type="COMMAND" if is_command else "TEXT",
            content=message_clean,
            metadata_={
                "parsed_intent": {
                    "is_command": is_command,
                    "risk": float(risk_match.group(1)) if risk_match else None,
                    "atr": float(atr_match.group(1)) if atr_match else None,
                    "rr": float(rr_match.group(1)) if rr_match else None,
                    "pause": is_pause,
                    "resume": is_resume,
                    "briefing": is_briefing_request,
                }
            },
            approval_status=None,
            is_test=is_test,
        )
        session.add(trader_msg)
        await session.commit()
        await session.refresh(trader_msg)

        # 3. Đọc dữ liệu hệ thống hiện tại
        current_params = await self.get_current_runtime_params()
        daily_dd = await self.calculate_daily_drawdown(session, include_test=is_test)

        guardrail_passed = True
        rejection_reasons: list[str] = []
        actions_taken: dict[str, Any] = {}
        proposed = dict(current_params)

        # 4. Xử lý kịch bản Briefing nếu người dùng yêu cầu
        if is_briefing_request and not (risk_match or atr_match or rr_match or is_pause or is_resume):
            briefing_res = await self.generate_executive_briefing(session, is_test=is_test)
            gov_msg = AgentTraderDialogue(
                sender="GOVERNOR",
                message_type="BRIEFING",
                content=briefing_res["briefing_text"],
                metadata_={
                    "linked_dialogue_id": trader_msg.id,
                    "guardrail_passed": True,
                    "is_briefing": True,
                    "daily_drawdown_pct": daily_dd,
                },
                approval_status=None,
                is_test=is_test,
            )
            session.add(gov_msg)
            await session.commit()
            await session.refresh(gov_msg)

            return {
                "trader_message_id": trader_msg.id,
                "governor_message_id": gov_msg.id,
                "response": briefing_res["briefing_text"],
                "actions_taken": {"generated_briefing": True},
                "guardrail_passed": True,
                "active_params": current_params,
            }

        # 5. Thẩm định Hard Guardrails đối với từng chỉ thị ghi đè
        if risk_match:
            req_risk = float(risk_match.group(1))
            if req_risk < 0.25 or req_risk > 1.50:
                guardrail_passed = False
                rejection_reasons.append(
                    f"Từ chối yêu cầu đặt mức rủi ro {req_risk:.2f}%. Theo Bộ Rào chắn Cứng (Hard Guardrails D21/D24) "
                    f"và Quy chế Bảo toàn Vốn (Capital Preservation Mandate), biên độ an toàn bắt buộc là [0.25%, 1.50%]. "
                    f"Yêu cầu vượt ngưỡng tối đa bị hủy bỏ để phòng ngừa rủi ro cháy tài khoản."
                )
            else:
                proposed["risk_per_trade_percent"] = req_risk
                actions_taken["risk_per_trade_percent"] = req_risk

        if atr_match:
            req_atr = float(atr_match.group(1))
            if req_atr < 1.00 or req_atr > 3.00:
                guardrail_passed = False
                rejection_reasons.append(
                    f"Từ chối điều chỉnh ATR SL Multiplier {req_atr:.2f}x. Dải an toàn cho phép là [1.00x, 3.00x] ATR "
                    f"để cân bằng giữa việc chống quét râu nến và bảo toàn khoảng cách dừng lỗ hợp lý."
                )
            else:
                proposed["atr_sl_multiplier"] = req_atr
                actions_taken["atr_sl_multiplier"] = req_atr

        if rr_match:
            req_rr = float(rr_match.group(1))
            if req_rr < 1.20 or req_rr > 4.00:
                guardrail_passed = False
                rejection_reasons.append(
                    f"Từ chối điều chỉnh Min Risk:Reward {req_rr:.2f}. Dải cho phép là [1.20, 4.00] để bảo đảm kỳ vọng toán học dương."
                )
            else:
                proposed["min_risk_reward_ratio"] = req_rr
                actions_taken["min_risk_reward_ratio"] = req_rr

        if is_pause:
            proposed["trading_allowed"] = False
            proposed["halt_reason"] = "TRADER_OVERRIDE: Tạm dừng giao dịch theo chỉ thị của Trader."
            actions_taken["trading_allowed"] = False
            actions_taken["halt_reason"] = proposed["halt_reason"]

        if is_resume:
            if daily_dd >= 3.00:
                guardrail_passed = False
                rejection_reasons.append(
                    f"Từ chối mở lại quyền giao dịch. Sụt giảm tài khoản trong ngày ({daily_dd:.2f}%) đã chạm ngưỡng tối đa 3.00% "
                    f"(Max Daily Drawdown Breaker). Hệ thống bị khóa cứng tuyệt đối cho đến ngày tiếp theo để bảo toàn vốn."
                )
            else:
                proposed["trading_allowed"] = True
                proposed["halt_reason"] = None
                actions_taken["trading_allowed"] = True

        # 6. Ra quyết định & Phản hồi
        active_params_dict = current_params
        if not guardrail_passed:
            reply_text = (
                "🛡️ **THÔNG BÁO TỪ BỘ RÀO CHẮN CỨNG (HARD GUARDRAILS):**\n"
                + "\n".join(f"• {r}" for r in rejection_reasons)
                + f"\n\n*Hệ thống bảo lưu nguyên vẹn bộ tham số hiện tại (Rủi ro: {current_params.get('risk_per_trade_percent')}%, Drawdown: {daily_dd:.2f}%).* "
            )
            msg_type = "TEXT"
        elif actions_taken:
            proposed["updated_by_agent"] = "TRADER_DIALOGUE_OVERRIDE"
            validated_params, was_hard_breached = validate_and_apply_hard_guardrails(
                proposed, current_daily_drawdown=daily_dd
            )
            if was_hard_breached:
                guardrail_passed = False
                reply_text = (
                    f"⚠️ Cảnh báo: Can thiệp bị chặn lại do Drawdown ngày đã đạt {daily_dd:.2f}% (ngưỡng 3.00%). "
                    f"Quyền giao dịch vẫn bị khóa cứng."
                )
                msg_type = "TEXT"
            else:
                await self._persist_and_sync_cache(session, validated_params)
                active_params_dict = validated_params.model_dump()
                actions_desc = []
                if "risk_per_trade_percent" in actions_taken:
                    actions_desc.append(f"Rủi ro / lệnh: **{actions_taken['risk_per_trade_percent']}%**")
                if "atr_sl_multiplier" in actions_taken:
                    actions_desc.append(f"ATR SL Multiplier: **{actions_taken['atr_sl_multiplier']}x**")
                if "min_risk_reward_ratio" in actions_taken:
                    actions_desc.append(f"Min R:R: **1:{actions_taken['min_risk_reward_ratio']}**")
                if "trading_allowed" in actions_taken:
                    state_str = "MỞ LẠI GIAO DỊCH" if actions_taken["trading_allowed"] else "TẠM DỪNG GIAO DỊCH"
                    actions_desc.append(f"Trạng thái: **{state_str}**")

                reply_text = (
                    f"✅ **CHỈ THỊ CỦA TRADER ĐÃ ĐƯỢC THI HÀNH THÀNH CÔNG:**\n"
                    f"Governor đã kiểm tra rào chắn an toàn và đồng bộ các thay đổi:\n"
                    + "\n".join(f"• {d}" for d in actions_desc)
                    + f"\n\n*Đã cập nhật Single Source of Truth trong PostgreSQL và đồng bộ tức thời sang Redis Cache.*"
                )
                msg_type = "OVERRIDE_CONFIRM"
        else:
            # Đối thoại thông thường không có câu lệnh
            reply_text = (
                f"Strategy Governor (CRO) đã tiếp nhận thông điệp từ Trader: *\"{message_clean}\"*.\n"
                f"Hệ thống hiện duy trì tham số: Rủi ro **{current_params.get('risk_per_trade_percent', 1.0):.2f}%**, "
                f"ATR SL **{current_params.get('atr_sl_multiplier', 1.5):.2f}x**, "
                f"Drawdown ngày **{daily_dd:.2f}%**, Trạng thái: **{'HOẠT ĐỘNG' if current_params.get('trading_allowed', True) else 'TẠM KHÓA'}**.\n"
                f"Trader có thể ra lệnh ghi đè (VD: *\"Hạ rủi ro xuống 0.5%\"*, *\"Tạm dừng giao dịch\"*) hoặc yêu cầu *\"Báo cáo điều hành\"* bất kỳ lúc nào."
            )
            msg_type = "TEXT"

        # 7. Ghi nhận phản hồi của Governor vào agent_trader_dialogue
        gov_msg = AgentTraderDialogue(
            conversation_id=conversation_id,
            target_agent="GOVERNOR",
            sender="GOVERNOR",
            message_type=msg_type,
            content=reply_text,
            metadata_={
                "linked_dialogue_id": trader_msg.id,
                "guardrail_passed": guardrail_passed,
                "actions_taken": actions_taken,
                "daily_drawdown_pct": daily_dd,
            },
            approval_status=None,
            is_test=is_test,
        )
        session.add(gov_msg)
        await session.commit()
        await session.refresh(gov_msg)

        # 8. Phát sóng Redis event
        try:
            await redis_client.publish(
                "agent:trader:dialogue",
                json.dumps({
                    "type": "agent.dialogue.message",
                    "conversation_id": conversation_id,
                    "trader_message": {
                        "id": trader_msg.id,
                        "conversation_id": conversation_id,
                        "sender": trader_msg.sender,
                        "content": trader_msg.content,
                        "timestamp": trader_msg.timestamp.isoformat(),
                    },
                    "governor_message": {
                        "id": gov_msg.id,
                        "conversation_id": conversation_id,
                        "sender": gov_msg.sender,
                        "message_type": gov_msg.message_type,
                        "content": gov_msg.content,
                        "guardrail_passed": guardrail_passed,
                        "actions_taken": actions_taken,
                        "timestamp": gov_msg.timestamp.isoformat(),
                    },
                }),
            )
        except Exception as e:
            logger.warning("Failed to publish dialogue event: %s", e)

        return {
            "trader_message_id": trader_msg.id,
            "governor_message_id": gov_msg.id,
            "response": reply_text,
            "actions_taken": actions_taken,
            "guardrail_passed": guardrail_passed,
            "active_params": active_params_dict,
        }

    async def respond_trade_approval(
        self,
        dialogue_id: int,
        action: str,
        session: AsyncSession,
        is_test: bool = False,
    ) -> dict[str, Any]:
        """
        Xử lý phản hồi phê duyệt / từ chối đề xuất mở lệnh từ Trader.
        Cập nhật trạng thái approval_status và tạo bản ghi phản hồi.
        """
        action_upper = action.strip().upper()
        if action_upper not in ["APPROVE", "REJECT"]:
            raise ValueError(
                f"Hành động phê duyệt không hợp lệ: '{action}'. Bắt buộc phải là 'APPROVE' hoặc 'REJECT'."
            )

        dialogue = await session.get(AgentTraderDialogue, dialogue_id)
        if not dialogue:
            raise ValueError(f"Không tìm thấy bản ghi đối thoại ID #{dialogue_id}")

        new_status = "APPROVED" if action_upper == "APPROVE" else "REJECTED"
        dialogue.approval_status = new_status

        if action_upper == "APPROVE":
            reply_text = (
                f"✅ **YÊU CẦU MỞ LỆNH #{dialogue_id} ĐÃ ĐƯỢC CHỦ THỂ PHÊ DUYỆT (APPROVED).**\n"
                f"Strategy Governor đã chuyển tiếp lệnh vào Auto Execution Engine để thực thi trên thị trường."
            )
        else:
            reply_text = (
                f"🛑 **YÊU CẦU MỞ LỆNH #{dialogue_id} ĐÃ BỊ TỪ CHỐI (REJECTED).**\n"
                f"Strategy Governor đã hủy bỏ thiết lập lệnh theo quyết định của Chủ thể."
            )

        gov_confirm = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="TEXT",
            content=reply_text,
            metadata_={
                "linked_dialogue_id": dialogue_id,
                "action": action_upper,
                "previous_status": "PENDING",
                "new_status": new_status,
            },
            approval_status=None,
            is_test=dialogue.is_test or is_test,
        )
        session.add(gov_confirm)
        await session.commit()
        await session.refresh(dialogue)
        await session.refresh(gov_confirm)

        try:
            event_payload = json.dumps({
                "type": "governor.approval_response",
                "dialogue_id": dialogue_id,
                "action": action_upper,
                "status": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await redis_client.publish("governor:approval_response", event_payload)
            await redis_client.publish("agent:trader:dialogue", event_payload)
        except Exception as e:
            logger.warning("Failed to publish approval response: %s", e)

        return {
            "dialogue_id": dialogue_id,
            "status": new_status,
            "message": reply_text,
            "confirmation_message_id": gov_confirm.id,
        }

    async def get_dialogue_history(
        self,
        session: AsyncSession,
        limit: int = 50,
        include_test: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Truy vấn lịch sử đối thoại giữa Trader và Governor.
        """
        stmt = select(AgentTraderDialogue)
        if not include_test:
            stmt = stmt.where(AgentTraderDialogue.is_test.is_(False))
        stmt = stmt.order_by(AgentTraderDialogue.timestamp.desc()).limit(limit)

        records = (await session.execute(stmt)).scalars().all()
        reversed_records = list(reversed(records))
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "sender": r.sender,
                "message_type": r.message_type,
                "content": r.content,
                "metadata": r.metadata_,
                "approval_status": r.approval_status,
            }
            for r in reversed_records
        ]


class GovernorWorker:
    """
    Worker chạy nền định kỳ mỗi 15 phút (hoặc theo sự kiện)
    để kích hoạt StrategyGovernor đánh giá và đồng bộ tham số tự động.
    """

    def __init__(self, governor: StrategyGovernor | None = None, interval_secs: int = 900):
        self.governor = governor or StrategyGovernor()
        self.interval_secs = interval_secs
        self._running = False
        self._task: asyncio.Task | None = None

    async def run(self) -> None:
        self._running = True
        logger.info("GovernorWorker started, evaluation interval: %ds", self.interval_secs)
        # Chạy đánh giá ban đầu sau khi khởi động 5 giây
        await asyncio.sleep(5.0)
        while self._running:
            try:
                async with session_factory() as session:
                    report = await self.governor.synthesize_consensus(session)
                    logger.info(
                        "Governor consensus updated: Allowed=%s, Risk=%.2f%%, ATR=%.2fx (Drawdown=%.2f%%)",
                        report.active_params.trading_allowed,
                        report.active_params.risk_per_trade_percent,
                        report.active_params.atr_sl_multiplier,
                        report.current_daily_drawdown_pct,
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Error in GovernorWorker evaluation loop: %s", exc)

            try:
                await asyncio.sleep(self.interval_secs)
            except asyncio.CancelledError:
                break

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


strategy_governor = StrategyGovernor()
governor_worker = GovernorWorker(strategy_governor, interval_secs=900)
