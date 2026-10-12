from datetime import datetime, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import delete

from ai_engine.technical_agent import (
    KnowledgeSubmissionRequest,
    technical_rag_agent,
)
from core.database import session_factory
from core.models import TradingKnowledge
from main import app


@pytest.mark.anyio
async def test_auto_classifier_multi_school():
    """Kiểm tra bộ tự động phân loại nhận diện chính xác các trường phái CMT, ICT, Wyckoff, Inducement/Traps, SMC"""
    # 1. Wyckoff Method
    wyckoff_text = (
        "Phase C Spring in accumulation schematic with climactic volume spread absorption. "
        "Smart money composite man absorbing selling climax."
    )
    res_wyckoff = technical_rag_agent.classify_text(wyckoff_text)
    assert res_wyckoff.detected_school == "WYCKOFF"
    assert res_wyckoff.suggested_category == "ACCUMULATION_SCHEMATIC"
    assert res_wyckoff.confidence >= 0.75
    assert "SPRING" in res_wyckoff.suggested_tags or "VSA" in res_wyckoff.suggested_tags

    # 2. ICT Methodology
    ict_text = (
        "London Open Kill Zone Judas Swing manipulation sweeping Asian liquidity pool. "
        "Displacement creates Fair Value Gap FVG targeting Optimal Trade Entry OTE."
    )
    res_ict = technical_rag_agent.classify_text(ict_text)
    assert res_ict.detected_school == "ICT"
    assert res_ict.suggested_category == "POWER_OF_3"
    assert res_ict.confidence >= 0.75

    # 3. Inducement & Trap Trading
    trap_text = (
        "Equal Lows EQL liquidity trap engineered before major POI. "
        "Retail trap inducement IDM sweep confirms institutional turtle soup setup."
    )
    res_trap = technical_rag_agent.classify_text(trap_text)
    assert res_trap.detected_school == "INDUCEMENT_TRAPS"
    assert res_trap.suggested_category == "LIQUIDITY_ENGINEERING"
    assert res_trap.confidence >= 0.75

    # 4. CMT Academic Framework
    cmt_text = (
        "CMT Dow Theory trend confirmation with support resistance polarity principle. "
        "Intermarket analysis shows DXY correlation and 10-year Treasury real yields divergence."
    )
    res_cmt = technical_rag_agent.classify_text(cmt_text)
    assert res_cmt.detected_school == "CMT"
    assert res_cmt.suggested_category == "INTERMARKET_MACRO"
    assert res_cmt.confidence >= 0.75

    # 5. SMC Baseline
    smc_text = "Bullish Order Block in discount zone following M15 Break of Structure BOS and CHoCH mitigation."
    res_smc = technical_rag_agent.classify_text(smc_text)
    assert res_smc.detected_school == "SMC"
    assert res_smc.suggested_category == "MARKET_STRUCTURE"


@pytest.mark.anyio
async def test_multi_school_knowledge_ingestion_and_vector_search():
    """Kiểm tra quy trình nạp tri thức đa trường phái với vector 1536d và tìm kiếm Cosine Distance có lọc school"""
    async with session_factory() as session:
        # Nạp tri thức Wyckoff test
        sub_wyckoff = KnowledgeSubmissionRequest(
            title="TEST Wyckoff Phase C Spring Accumulation",
            school_of_thought="WYCKOFF",
            category="TEST",
            sub_categories=["PHASE_C", "SPRING"],
            tags=["SPRING", "VSA"],
            academic_reference="TEST Wyckoff 1931",
            content="TEST Spring in Phase C shakes out retail sellers and absorbs volume before markup.",
            source_type="TEST",
            confidence_score=0.95,
        )
        id_wyckoff = await technical_rag_agent.ingest_knowledge(sub_wyckoff, session)
        assert id_wyckoff > 0

        # Nạp tri thức ICT test
        sub_ict = KnowledgeSubmissionRequest(
            title="TEST ICT Judas Swing London Open Sweep",
            school_of_thought="ICT",
            category="TEST",
            sub_categories=["JUDAS_SWING", "LONDON_OPEN"],
            tags=["AMD", "IPDA"],
            academic_reference="TEST ICT IPDA",
            content="TEST London Open Judas swing sweeps Asian high/low creating false directional move.",
            source_type="TEST",
            confidence_score=0.92,
        )
        id_ict = await technical_rag_agent.ingest_knowledge(sub_ict, session)
        assert id_ict > 0

        # Truy vấn tri thức Wyckoff có lọc school_of_thought
        results_wyckoff = await technical_rag_agent.search_multi_school(
            query="Wyckoff spring phase C volume shakeout",
            school_of_thought="WYCKOFF",
            top_k=3,
            include_test=True,
            session=session,
        )
        assert len(results_wyckoff) >= 1
        assert any("TEST Wyckoff" in r.title for r in results_wyckoff)
        assert any(r.school_of_thought == "WYCKOFF" for r in results_wyckoff)

        # Truy vấn tri thức ICT có lọc school_of_thought
        results_ict = await technical_rag_agent.search_multi_school(
            query="Judas swing manipulation in London open session",
            school_of_thought="ICT",
            top_k=3,
            include_test=True,
            session=session,
        )
        assert len(results_ict) >= 1
        assert any("TEST ICT" in r.title for r in results_ict)
        assert any(r.school_of_thought == "ICT" for r in results_ict)


@pytest.mark.anyio
async def test_generate_technical_analysis_cross_school_confluence():
    """Kiểm tra báo cáo phân tích kỹ thuật hợp lưu đa trường phái (Wyckoff, ICT, Inducement, CMT, SMC)"""
    async with session_factory() as session:
        report = await technical_rag_agent.generate_technical_analysis(
            session=session, symbol="XAUUSD", timeframe="M15"
        )

        assert report.agent == "TECHNICAL_RAG_AGENT"
        assert report.timeframe_focus == "M15"
        assert report.structural_bias in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert report.confidence_score >= 0.50
        assert report.primary_school in [
            "WYCKOFF", "ICT", "CMT", "INDUCEMENT_TRAPS", "SMC", "GENERAL"
        ]
        assert len(report.confluent_schools) >= 2

        # Kiểm tra chi tiết từng trường phái
        cross = report.cross_school_analysis
        assert "wyckoff" in cross
        assert "ict" in cross
        assert "inducement_and_traps" in cross
        assert "cmt_academic" in cross
        assert "smc" in cross

        assert "phase" in cross["wyckoff"]
        assert "session" in cross["ict"]
        assert "idm_cleared" in cross["inducement_and_traps"]
        assert "dow_trend" in cross["cmt_academic"]

        # Kiểm tra khuyến nghị lệnh giao dịch
        assert report.suggested_trade_setup is not None
        assert report.suggested_trade_setup.action in ["BUY", "SELL", "WAIT"]
        assert len(report.suggested_trade_setup.entry_zone) == 2
        assert report.suggested_trade_setup.planned_risk_reward >= 1.5


@pytest.mark.anyio
async def test_school_statistics_aggregation():
    """Kiểm tra thống kê các trường phái trong Vector DB"""
    async with session_factory() as session:
        stats = await technical_rag_agent.get_school_statistics(session)
        assert "schools" in stats
        assert "total_chunks" in stats
        assert isinstance(stats["schools"], list)


@pytest.mark.anyio
async def test_technical_agent_rest_api_endpoints():
    """Kiểm tra toàn bộ 5 REST API endpoints của Technical RAG Agent"""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. GET /api/v1/agents/technical/analysis
        res_analysis = await client.get("/api/v1/agents/technical/analysis")
        assert res_analysis.status_code == 200
        analysis_data = res_analysis.json()
        assert analysis_data["agent"] == "TECHNICAL_RAG_AGENT"
        assert "cross_school_analysis" in analysis_data
        assert "suggested_trade_setup" in analysis_data

        # 2. POST /api/v1/agents/technical/knowledge/classify
        res_classify = await client.post(
            "/api/v1/agents/technical/knowledge/classify",
            json={
                "text": "Wyckoff Phase C Spring with climactic volume absorption and composite man accumulation."
            },
        )
        assert res_classify.status_code == 200
        classify_data = res_classify.json()
        assert classify_data["status"] == "success"
        assert classify_data["result"]["detected_school"] == "WYCKOFF"

        # 3. POST /api/v1/agents/technical/knowledge/submit
        res_submit = await client.post(
            "/api/v1/agents/technical/knowledge/submit",
            json={
                "title": "TEST CMT Intermarket Gold and DXY Correlation Rule",
                "school_of_thought": "CMT",
                "category": "TEST",
                "sub_categories": ["DXY", "REAL_YIELDS"],
                "tags": ["TEST_INTERMARKET", "CMT"],
                "academic_reference": "TEST John Murphy Intermarket",
                "content": "TEST Gold price moves inversely with the US Dollar Index DXY and Treasury yields.",
                "source_type": "TEST",
                "confidence_score": 0.95,
                "verified_by_trader": True,
            },
        )
        assert res_submit.status_code == 200
        submit_data = res_submit.json()
        assert submit_data["status"] == "success"
        assert submit_data["school_of_thought"] == "CMT"
        assert submit_data["id"] > 0

        # 4. GET /api/v1/agents/technical/knowledge/schools
        res_schools = await client.get("/api/v1/agents/technical/knowledge/schools")
        assert res_schools.status_code == 200
        schools_data = res_schools.json()
        assert "schools" in schools_data
        assert "total_chunks" in schools_data

        # 5. GET /api/v1/agents/technical/knowledge/search
        res_search = await client.get(
            "/api/v1/agents/technical/knowledge/search",
            params={"query": "CMT DXY correlation and real yields", "school_of_thought": "CMT"},
        )
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert isinstance(search_data, list)
