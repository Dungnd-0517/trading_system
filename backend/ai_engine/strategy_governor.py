import asyncio
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import json
import logging
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_guard import news_circuit_breaker
from ai_engine.reflexion_service import reflexion_service
from core.database import session_factory
from core.models import (
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
        self, session: AsyncSession, include_test: bool = False
    ) -> ConsensusReport:
        """
        Tổng hợp đồng thuận (Consensus) từ 3 Agent và áp dụng Hard Guardrails:
        - News Agent: Sentiment và Circuit Breaker.
        - Technical RAG: Volatility regime và ATR.
        - Reflexion Agent: Các lỗi sai lầm gần nhất.
        """
        now = datetime.now(timezone.utc)

        # 1. Thu thập dữ liệu News Agent
        is_news_halt, news_reason, _ = await news_circuit_breaker.is_circuit_active(
            session, now
        )

        news_stmt = (
            select(func.avg(FinancialNews.sentiment_score))
            .where(FinancialNews.published_at >= now - timedelta(hours=3))
        )
        avg_sentiment = (await session.execute(news_stmt)).scalar()
        sentiment_score = float(avg_sentiment) if avg_sentiment is not None else 0.0

        # 2. Thu thập dữ liệu Technical Agent
        regime, current_atr = await self.evaluate_market_regime(session)

        # 3. Thu thập dữ liệu Reflexion Agent
        recent_losses, mistake_patterns = await self.review_recent_reflexions(
            session, include_test=include_test
        )

        # 4. Tính toán Daily Drawdown
        daily_dd = await self.calculate_daily_drawdown(
            session, include_test=include_test
        )

        # 5. Logic đề xuất thích ứng của Governor
        suggested_risk = 1.00
        suggested_atr_multiplier = 1.50
        suggested_rr = 1.50
        trading_allowed = True
        halt_reason = None
        bias = "NEUTRAL"
        confidence = 0.80
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
