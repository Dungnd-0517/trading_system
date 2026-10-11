from datetime import datetime, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select

from ai_engine.reflexion_service import reflexion_agent
from core.database import session_factory
from core.models import EpisodicTradeMemory, TradingKnowledge
from main import app


@pytest.mark.anyio
async def test_reflexion_learning_analytics_and_repeated_mistakes():
    """Kiểm tra thống kê đường cong học tập, tần suất lỗi lặp lại và phát hiện ứng viên thăng cấp quy tắc"""
    async with session_factory() as session:
        # Tạo chuỗi ký ức giao dịch test
        m1 = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="TEST XAUUSD Buy 2650.0 reached SL 2635.0",
            root_cause="Stop loss was too tight for London open wicks",
            lesson_learned="Buffer SL by at least 1.8x ATR",
            mistake_category="SL_TOO_TIGHT",
            rule_to_add="Expand atr_sl_multiplier to 1.80x during London session",
            is_test=True,
        )
        m2 = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="TEST XAUUSD Sell 2660.0 wicked out by high sweep",
            root_cause="Stop loss distance only 12 points",
            lesson_learned="Buffer SL properly",
            mistake_category="SL_TOO_TIGHT",
            rule_to_add="Expand atr_sl_multiplier to 1.80x during London session",
            is_test=True,
        )
        m3 = EpisodicTradeMemory(
            outcome="WIN",
            market_context_summary="TEST XAUUSD Buy 2640.0 reached TP 2670.0",
            root_cause="Respected HTF discount zone and London Killzone",
            lesson_learned="Patience on HTF POI yields edge",
            mistake_category=None,
            rule_to_add="Maintain HTF confluence rules",
            is_test=True,
        )
        session.add_all([m1, m2, m3])
        await session.commit()

        # Gọi analytics
        analytics = await reflexion_agent.get_learning_analytics(include_test=True, session=session)

        assert analytics["total_memories"] >= 3
        assert "SL_TOO_TIGHT" in analytics["repeated_mistake_frequency"]
        assert analytics["repeated_mistake_frequency"]["SL_TOO_TIGHT"] >= 2

        # Kiểm tra phát hiện ứng viên thăng cấp quy tắc (Candidate for Promotion)
        candidates = analytics["candidates_for_promotion"]
        assert len(candidates) >= 1
        sl_cand = next((c for c in candidates if c["mistake_category"] == "SL_TOO_TIGHT"), None)
        assert sl_cand is not None
        assert sl_cand["frequency"] >= 2
        assert sl_cand["status"] in ["READY_FOR_PROMOTION", "ALREADY_PROMOTED"]
        assert "atr_sl_multiplier" in sl_cand["suggested_rule"]


@pytest.mark.anyio
async def test_reflexion_rule_promotion_to_trading_knowledge():
    """Kiểm tra thăng cấp bài học từ episodic_trade_memory thành tri thức chính thức trong trading_knowledge"""
    async with session_factory() as session:
        # 1. Tạo ký ức test
        test_mem = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="TEST XAUUSD Sell at London open got wicked out",
            root_cause="SL placed within Asian high wick zone",
            lesson_learned="Never place SL inside equal highs liquidity pool",
            mistake_category="SL_TOO_TIGHT",
            rule_to_add="Tự động nới atr_sl_multiplier từ 1.5 lên 1.8 - 2.0 khi giao dịch trong 45 phút đầu của phiên Luân Đôn.",
            is_test=True,
        )
        session.add(test_mem)
        await session.commit()
        await session.refresh(test_mem)
        mem_id = test_mem.id

        # 2. Thăng cấp ký ức thành quy tắc
        res = await reflexion_agent.promote_memory_to_rule(memory_id=mem_id, session=session)

        assert res["status"] == "PROMOTED"
        assert res["memory_id"] == mem_id
        assert res["knowledge_id"] > 0
        assert "SL_TOO_TIGHT" in res["title"]

        # 3. Kiểm tra bản ghi trong bảng trading_knowledge
        knowledge = await session.get(TradingKnowledge, res["knowledge_id"])
        assert knowledge is not None
        assert knowledge.title == res["title"]
        assert knowledge.source_type == "TEST"  # Vì is_test=True nên source_type là TEST để D18 tự dọn dẹp
        assert knowledge.metadata_["tags"] == ["REFLEXION", "PROMOTED_RULE", "SL_TOO_TIGHT"]
        assert knowledge.metadata_["promoted_from_memory_id"] == mem_id
        assert len(knowledge.embedding) == 1536


@pytest.mark.anyio
async def test_reflexion_feedback_report_generation():
    """Kiểm tra tạo báo cáo phản hồi ReflexionFeedbackReport chuẩn xác cho một lệnh đóng"""
    async with session_factory() as session:
        test_mem = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="TEST XAUUSD Buy 2650 reached SL",
            root_cause="Entered before M15 candle closed",
            lesson_learned="Wait for full candle close confirmation",
            mistake_category="EARLY_ENTRY",
            rule_to_add="Require closed M15 candle confirmation instead of touch entry.",
            is_test=True,
        )
        session.add(test_mem)
        await session.commit()
        await session.refresh(test_mem)

        report = await reflexion_agent.generate_feedback_report(order_id=test_mem.id, session=session)

        assert report["agent"] == "REFLEXION_AGENT"
        assert report["outcome"] == "LOSS"
        assert report["mistake_category"] == "EARLY_ENTRY"
        assert "closed" in report["root_cause_analysis"].lower() or "candle" in report["root_cause_analysis"].lower()
        assert "confirmation" in report["rule_to_add"].lower()
        assert report["promotion_status"] in ["READY_FOR_GOVERNOR_APPROVAL", "EVALUATED_MONITORING"]
        assert "total_memories" in report["learning_analytics"]


@pytest.mark.anyio
async def test_reflexion_agent_rest_api_endpoints():
    """Kiểm tra toàn bộ các REST API endpoints của Reflexion Agent (/api/v1/agents/reflexion)"""
    async with session_factory() as session:
        test_mem = EpisodicTradeMemory(
            outcome="LOSS",
            market_context_summary="TEST Api memory test",
            root_cause="Wicked out by news spike",
            lesson_learned="Obey news circuit breaker",
            mistake_category="TRADED_DURING_NEWS_SPIKE",
            rule_to_add="Halt trading 30 minutes around red-flag releases",
            is_test=True,
        )
        session.add(test_mem)
        await session.commit()
        await session.refresh(test_mem)
        target_id = test_mem.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. GET /api/v1/agents/reflexion/analytics
        res_analytics = await client.get("/api/v1/agents/reflexion/analytics?include_test=true")
        assert res_analytics.status_code == 200
        data_analytics = res_analytics.json()
        assert data_analytics["total_memories"] >= 1
        assert "repeated_mistake_frequency" in data_analytics

        # 2. POST /api/v1/agents/reflexion/promote-rule/{memory_id}
        res_promote = await client.post(f"/api/v1/agents/reflexion/promote-rule/{target_id}")
        assert res_promote.status_code == 200
        data_promote = res_promote.json()
        assert data_promote["status"] == "PROMOTED"
        assert data_promote["knowledge_id"] > 0

        # 3. GET /api/v1/agents/reflexion/feedback-report/{order_id}
        res_feedback = await client.get(f"/api/v1/agents/reflexion/feedback-report/{target_id}")
        assert res_feedback.status_code == 200
        data_feedback = res_feedback.json()
        assert data_feedback["agent"] == "REFLEXION_AGENT"
        assert data_feedback["mistake_category"] == "TRADED_DURING_NEWS_SPIKE"

        # 4. GET /api/v1/agents/reflexion/memories
        res_memories = await client.get("/api/v1/agents/reflexion/memories?include_test=true&limit=5")
        assert res_memories.status_code == 200
        data_memories = res_memories.json()
        assert isinstance(data_memories, list)
        assert len(data_memories) >= 1

        # 5. GET /api/v1/agents/reflexion/search
        res_search = await client.get(
            "/api/v1/agents/reflexion/search",
            params={"query": "news spike buffer circuit breaker", "include_test": "true"},
        )
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert isinstance(data_search, list)
