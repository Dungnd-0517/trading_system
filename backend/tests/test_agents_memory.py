from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select, delete
from datetime import datetime, timezone

from core.database import session_factory
from core.models import (
    TradingKnowledge,
    EpisodicTradeMemory,
    SimulatedOrder,
    SystemTradingConfig,
)


def make_mock_embedding(seed: float = 1.0) -> list[float]:
    """Tạo vector 1536 chiều giả lập cho unit test"""
    vec = [0.0] * 1536
    vec[0] = seed
    vec[1] = 1.0 - abs(seed)
    return vec


@pytest.mark.anyio
async def test_trading_knowledge_crud_and_vector_search():
    """Kiểm tra lưu trữ tri thức RAG và truy vấn semantic search bằng khoảng cách cosine"""
    async with session_factory() as session:
        # 1. Tạo 2 tài liệu tri thức
        k1 = TradingKnowledge(
            title="SMC Fair Value Gap Strategy",
            category="TEST",
            content="When an FVG occurs during London open, wait for retest before placing limit order.",
            metadata_={"author": "ICT", "timeframe": "M15", "topic": "FVG"},
            embedding=make_mock_embedding(0.9),
        )
        k2 = TradingKnowledge(
            title="Macro Risk Management around CPI",
            category="TEST",
            content="Halt trading 30 minutes before and after high-impact CPI release.",
            metadata_={"author": "RiskGovernor", "category": "Macro"},
            embedding=make_mock_embedding(0.1),
        )
        session.add_all([k1, k2])
        await session.commit()

        # 2. Tìm kiếm vector tương đồng gần k1 nhất (seed = 0.95)
        query_vec = make_mock_embedding(0.95)
        stmt = (
            select(TradingKnowledge)
            .where(TradingKnowledge.category == "TEST")
            .order_by(TradingKnowledge.embedding.cosine_distance(query_vec))
            .limit(1)
        )
        result = await session.execute(stmt)
        closest = result.scalar_one_or_none()

        assert closest is not None
        assert closest.title == "SMC Fair Value Gap Strategy"
        assert closest.metadata_["author"] == "ICT"
        assert closest.metadata_["topic"] == "FVG"


@pytest.mark.anyio
async def test_episodic_trade_memory_and_cascade_delete():
    """Kiểm tra lưu trữ ký ức lệnh Reflexion, gắn cờ is_test và cascade delete khi xóa lệnh"""
    async with session_factory() as session:
        # 1. Tạo lệnh test mô phỏng
        order = SimulatedOrder(
            symbol="XAUUSD",
            order_type="BUY",
            status="CLOSED",
            lot_size=Decimal("0.10"),
            entry_price=Decimal("2650.00"),
            exit_price=Decimal("2645.00"),
            stop_loss=Decimal("2645.00"),
            take_profit=Decimal("2665.00"),
            realized_pnl=Decimal("-50.00"),
            close_reason="SL_HIT",
            strategy_trigger="SMC_ORDER_BLOCK",
            is_test=True,
            open_time=datetime.now(timezone.utc),
            close_time=datetime.now(timezone.utc),
        )
        session.add(order)
        await session.flush()

        # 2. Tạo ký ức Reflexion rút kinh nghiệm từ lệnh thua
        memory = EpisodicTradeMemory(
            order_id=order.id,
            outcome="LOSS",
            market_context_summary="XAUUSD broke down sharply right after Non-Farm Payrolls release",
            root_cause="Entered prematurely without waiting for 15M candle confirmation close",
            lesson_learned="Avoid immediate market execution within 15 minutes of NFP release",
            mistake_category="EARLY_ENTRY",
            rule_to_add="Wait for M15 market structure shift confirmation post-news",
            embedding=make_mock_embedding(0.8),
            is_test=True,
        )
        session.add(memory)
        await session.commit()

        # 3. Truy vấn ký ức theo cosine distance và mistake_category
        query_vec = make_mock_embedding(0.85)
        stmt = (
            select(EpisodicTradeMemory)
            .where(
                EpisodicTradeMemory.is_test.is_(True),
                EpisodicTradeMemory.mistake_category == "EARLY_ENTRY",
            )
            .order_by(EpisodicTradeMemory.embedding.cosine_distance(query_vec))
        )
        memories = (await session.execute(stmt)).scalars().all()
        assert len(memories) >= 1
        assert memories[0].outcome == "LOSS"
        assert memories[0].order_id == order.id

        mem_id = memory.id

        # 4. Kiểm tra cascade delete: khi xóa SimulatedOrder, memory tương ứng cũng tự động bị xóa
        await session.execute(delete(SimulatedOrder).where(SimulatedOrder.id == order.id))
        await session.commit()

        stmt_check = select(EpisodicTradeMemory).where(EpisodicTradeMemory.id == mem_id)
        check_mem = (await session.execute(stmt_check)).scalar_one_or_none()
        assert check_mem is None


@pytest.mark.anyio
async def test_system_trading_config_dynamic_ai_parameters():
    """Kiểm tra các tham số AI thích ứng trong SystemTradingConfig"""
    async with session_factory() as session:
        config = await session.get(SystemTradingConfig, 1)
        assert config is not None

        # Kiểm tra giá trị mặc định ban đầu
        assert config.atr_sl_multiplier == Decimal("1.50")
        assert config.min_risk_reward_ratio == Decimal("1.50")
        assert config.trading_allowed is True
        assert config.updated_by_agent is not None

        # Mô phỏng AI Governor điều chỉnh thông số khi biến động thị trường tăng cao
        old_multiplier = config.atr_sl_multiplier
        old_agent = config.updated_by_agent

        config.atr_sl_multiplier = Decimal("2.25")
        config.min_risk_reward_ratio = Decimal("1.80")
        config.trading_allowed = False
        config.halt_reason = "High volatility warning: geopolitical tensions"
        config.updated_by_agent = "RISK_GOVERNOR_AGENT"
        await session.commit()

        # Re-fetch và kiểm tra
        updated_config = await session.get(SystemTradingConfig, 1)
        assert updated_config.atr_sl_multiplier == Decimal("2.25")
        assert updated_config.min_risk_reward_ratio == Decimal("1.80")
        assert updated_config.trading_allowed is False
        assert updated_config.halt_reason == "High volatility warning: geopolitical tensions"
        assert updated_config.updated_by_agent == "RISK_GOVERNOR_AGENT"

        # Khôi phục trạng thái chuẩn
        updated_config.atr_sl_multiplier = old_multiplier
        updated_config.min_risk_reward_ratio = Decimal("1.50")
        updated_config.trading_allowed = True
        updated_config.halt_reason = None
        updated_config.updated_by_agent = old_agent
        await session.commit()
