from decimal import Decimal
import pytest
from sqlalchemy import func, select

from core.database import session_factory
from core.models import (
    AgentDecisionLog,
    AgentTraderDialogue,
    TradingKnowledge,
)


@pytest.mark.anyio
async def test_agent_decision_log_model():
    """Kiểm tra lưu trữ và truy vấn nhật ký quyết định AgentDecisionLog (Task 1 Phase 3 Sprint 2)"""
    async with session_factory() as session:
        log_entry = AgentDecisionLog(
            market_regime="TRENDING_EXPANSION",
            suggested_bias="BULLISH",
            consensus_score=Decimal("0.85"),
            technical_confidence=Decimal("0.90"),
            macro_sentiment_score=Decimal("0.45"),
            active_circuit_breaker=False,
            applied_risk_pct=Decimal("1.00"),
            applied_sl_mult=Decimal("1.50"),
            applied_min_rr=Decimal("2.00"),
            trading_allowed=True,
            halt_reason=None,
            rationale_summary="Đồng thuận 3 Agent ủng hộ setup BUY Vàng: Wyckoff Phase C Spring kết hợp tin vĩ mô ôn hòa.",
            agent_votes={
                "technical": {"vote": "BUY", "confidence": 0.90, "school": "WYCKOFF"},
                "macro": {"vote": "BUY", "sentiment": 0.45, "circuit_active": False},
                "reflexion": {"vote": "BUY", "repeated_mistake_risk": "LOW"},
            },
            is_test=True,
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)

        assert log_entry.id is not None
        assert log_entry.market_regime == "TRENDING_EXPANSION"
        assert log_entry.consensus_score == Decimal("0.85")
        assert log_entry.agent_votes["technical"]["school"] == "WYCKOFF"
        assert log_entry.is_test is True

        # Query kiểm tra index
        stmt = (
            select(AgentDecisionLog)
            .where(AgentDecisionLog.id == log_entry.id)
        )
        found = (await session.scalars(stmt)).first()
        assert found is not None
        assert found.rationale_summary.startswith("Đồng thuận")


@pytest.mark.anyio
async def test_agent_trader_dialogue_model():
    """Kiểm tra mô hình đối thoại hai chiều giữa Trader và Strategy Governor"""
    async with session_factory() as session:
        dialogue = AgentTraderDialogue(
            sender="TRADER",
            message_type="COMMAND",
            content="Hạ rủi ro mỗi lệnh xuống 0.5% và nới SL lên 2.0x ATR trong phiên Mỹ",
            metadata_={
                "parsed_intent": "OVERRIDE_PARAMS",
                "proposed_risk_pct": 0.5,
                "proposed_sl_mult": 2.0,
                "session": "NY_SESSION",
            },
            approval_status="PENDING",
            is_test=True,
        )
        session.add(dialogue)
        await session.commit()
        await session.refresh(dialogue)

        assert dialogue.id is not None
        assert dialogue.sender == "TRADER"
        assert dialogue.message_type == "COMMAND"
        assert dialogue.approval_status == "PENDING"
        assert dialogue.metadata_["proposed_risk_pct"] == 0.5
        assert dialogue.is_test is True

        # Kiểm tra phản hồi từ Governor
        gov_reply = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="OVERRIDE_CONFIRM",
            content="Đã xác thực qua Hard Guardrails và áp dụng tham số rủi ro 0.5%, SL Multiplier 2.0x thành công.",
            metadata_={"linked_dialogue_id": dialogue.id, "guardrail_passed": True},
            approval_status="APPROVED",
            is_test=True,
        )
        session.add(gov_reply)
        await session.commit()
        await session.refresh(gov_reply)

        assert gov_reply.id is not None
        assert gov_reply.sender == "GOVERNOR"
        assert gov_reply.approval_status == "APPROVED"


@pytest.mark.anyio
async def test_trading_knowledge_multi_school_and_metadata():
    """Kiểm tra các trường mở rộng của TradingKnowledge: school_of_thought, source_type, metadata JSONB"""
    fake_vector = [0.01 * (i % 10) for i in range(1536)]

    async with session_factory() as session:
        # Nạp tri thức Wyckoff
        wyckoff_doc = TradingKnowledge(
            title="Wyckoff Accumulation Phase C Spring Analysis",
            school_of_thought="WYCKOFF",
            category="ACCUMULATION_SCHEMATIC",
            content="Spring là cú rũ bỏ thanh khoản cuối cùng trước khi giá bước vào giai đoạn Markup SOS.",
            source_type="TRADER_PROVIDED",
            verified_by_trader=True,
            confidence_score=Decimal("0.95"),
            metadata_={
                "school_of_thought": "WYCKOFF",
                "sub_categories": ["PHASE_C", "SPRING", "SOS"],
                "tags": ["VSA", "EFFORT_VS_RESULT", "COMPOSITE_MAN"],
                "academic_reference": "Richard D. Wyckoff Method (1931)",
                "applicable_timeframes": ["M15", "H1", "H4"],
                "is_test": True,
            },
            embedding=fake_vector,
        )
        session.add(wyckoff_doc)

        # Nạp tri thức ICT
        ict_doc = TradingKnowledge(
            title="ICT Power of 3 (AMD) Judas Swing at London Open",
            school_of_thought="ICT",
            category="POWER_OF_3",
            content="Judas Swing là chuyển động bẫy thanh khoản giả tạo đầu phiên trước khi mở ra xu hướng thật.",
            source_type="TEST",
            verified_by_trader=True,
            confidence_score=Decimal("0.90"),
            metadata_={
                "school_of_thought": "ICT",
                "sub_categories": ["MANIPULATION", "JUDAS_SWING"],
                "tags": ["IPDA", "KILL_ZONE", "LIQUIDITY_RUN"],
                "academic_reference": "ICT Mentorship",
                "applicable_timeframes": ["M15"],
                "is_test": True,
            },
            embedding=fake_vector,
        )
        session.add(ict_doc)
        await session.commit()

        # Query lọc theo school_of_thought
        wyckoff_rows = (
            await session.scalars(
                select(TradingKnowledge).where(TradingKnowledge.school_of_thought == "WYCKOFF")
            )
        ).all()
        assert len(wyckoff_rows) >= 1
        found_wyckoff = next(r for r in wyckoff_rows if r.title == wyckoff_doc.title)
        assert found_wyckoff.school_of_thought == "WYCKOFF"
        assert found_wyckoff.source_type == "TRADER_PROVIDED"
        assert found_wyckoff.confidence_score == Decimal("0.95")
        assert "EFFORT_VS_RESULT" in found_wyckoff.metadata_["tags"]

        # Query lọc theo source_type
        test_src_rows = (
            await session.scalars(
                select(TradingKnowledge).where(TradingKnowledge.source_type == "TEST")
            )
        ).all()
        assert any(r.title == ict_doc.title for r in test_src_rows)


@pytest.mark.anyio
async def test_d18_isolation_clean_verification():
    """Kiểm tra chuẩn cách ly D18: Các bản ghi test được dọn dẹp sạch sẽ sau test"""
    async with session_factory() as session:
        # Kiểm tra trước khi insert
        test_decisions = await session.scalar(
            select(func.count(AgentDecisionLog.id)).where(AgentDecisionLog.is_test.is_(True))
        )
        test_dialogues = await session.scalar(
            select(func.count(AgentTraderDialogue.id)).where(AgentTraderDialogue.is_test.is_(True))
        )
        # Nhờ autouse fixture conftest.py, sau mỗi test run, số lượng bản ghi is_test=True phải bằng 0
        assert test_decisions == 0
        assert test_dialogues == 0
