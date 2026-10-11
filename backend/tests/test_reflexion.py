from datetime import datetime, timedelta, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select, delete

from ai_engine.reflexion_service import reflexion_service
from core.database import session_factory
from core.models import EconomicEvent, EpisodicTradeMemory, SimulatedOrder
from main import app


@pytest.mark.anyio
async def test_reflexion_sl_too_tight_analysis():
    """Kiểm tra phân tích lệnh thua do đặt SL quá ngắn (SL_TOO_TIGHT)"""
    now = datetime.now(timezone.utc)
    order_data = {
        "id": 99901,
        "symbol": "XAUUSD",
        "order_type": "BUY",
        "entry_price": 2650.0,
        "exit_price": 2636.0,
        "stop_loss": 2635.0,  # Khoảng cách 15 points <= 20
        "take_profit": 2680.0,
        "realized_pnl": -45.0,
        "close_reason": "SL_HIT",
        "open_time": (now - timedelta(minutes=20)).isoformat(),
        "close_time": now.isoformat(),
        "is_test": True,
        "strategy_trigger": "SMC_ORDER_BLOCK",
    }

    memory = await reflexion_service.analyze_closed_order(order_data)
    assert memory.outcome == "LOSS"
    assert memory.mistake_category == "SL_TOO_TIGHT"
    assert "spread and wick noise" in memory.root_cause
    assert "ATR buffer" in memory.lesson_learned
    assert "atr_sl_multiplier" in memory.rule_to_add
    assert len(memory.embedding) == 1536
    assert memory.is_test is True


@pytest.mark.anyio
async def test_reflexion_early_entry_analysis():
    """Kiểm tra phân tích lệnh thua do vào lệnh quá sớm trước khi đóng nến xác nhận (EARLY_ENTRY)"""
    now = datetime.now(timezone.utc)
    order_data = {
        "id": 99902,
        "symbol": "XAUUSD",
        "order_type": "SELL",
        "entry_price": 2660.0,
        "exit_price": 2685.0,
        "stop_loss": 2685.0,  # Khoảng cách 25 points > 20
        "take_profit": 2620.0,
        "realized_pnl": -75.0,
        "close_reason": "SL_HIT",
        "open_time": (now - timedelta(seconds=90)).isoformat(),  # Thời gian giữ chỉ 90s < 180s
        "close_time": now.isoformat(),
        "is_test": True,
        "strategy_trigger": "SMC_CHUCH_M15",
    }

    memory = await reflexion_service.analyze_closed_order(order_data)
    assert memory.outcome == "LOSS"
    assert memory.mistake_category == "EARLY_ENTRY"
    assert "front-running" in memory.root_cause
    assert "CHoCH" in memory.lesson_learned
    assert "M15" in memory.rule_to_add


@pytest.mark.anyio
async def test_reflexion_news_spike_analysis():
    """Kiểm tra phân tích lệnh thua do dính bão tin tức đỏ vĩ mô (TRADED_DURING_NEWS_SPIKE)"""
    now = datetime.now(timezone.utc)

    # Tạo một sự kiện kinh tế 3 sao trong DB
    async with session_factory() as session:
        event = EconomicEvent(
            source="TEST_FEED",
            title="US Consumer Price Index (CPI) YoY",
            event_timestamp=now - timedelta(minutes=5),
            timezone_status="VERIFIED",
            currency="USD",
            provider_time_raw="08:30 AM",
            impact_stars=3,
            classification_status="CLASSIFIED",
        )
        session.add(event)
        await session.commit()
        event_id = event.id

    try:
        order_data = {
            "id": 99903,
            "symbol": "XAUUSD",
            "order_type": "BUY",
            "entry_price": 2640.0,
            "exit_price": 2610.0,
            "stop_loss": 2610.0,
            "take_profit": 2680.0,
            "realized_pnl": -120.0,
            "close_reason": "SL_HIT",
            "open_time": (now - timedelta(minutes=15)).isoformat(),
            "close_time": now.isoformat(),
            "is_test": True,
        }

        memory = await reflexion_service.analyze_closed_order(order_data)
        assert memory.outcome == "LOSS"
        assert memory.mistake_category == "TRADED_DURING_NEWS_SPIKE"
        assert "Consumer Price Index" in memory.root_cause
        assert "Circuit Breaker" in memory.lesson_learned
    finally:
        # Xóa sự kiện kinh tế test
        async with session_factory() as session:
            await session.execute(delete(EconomicEvent).where(EconomicEvent.id == event_id))
            await session.commit()


@pytest.mark.anyio
async def test_reflexion_win_and_breakeven_analysis():
    """Kiểm tra phân tích lệnh thắng (WIN) và lệnh hòa vốn (BREAKEVEN)"""
    now = datetime.now(timezone.utc)

    # 1. Lệnh WIN
    win_data = {
        "id": 99904,
        "symbol": "XAUUSD",
        "order_type": "BUY",
        "entry_price": 2640.0,
        "exit_price": 2670.0,
        "stop_loss": 2625.0,
        "take_profit": 2670.0,
        "realized_pnl": 90.0,
        "close_reason": "TP_HIT",
        "open_time": (now - timedelta(hours=1)).isoformat(),
        "close_time": now.isoformat(),
        "is_test": True,
    }
    win_mem = await reflexion_service.analyze_closed_order(win_data)
    assert win_mem.outcome == "WIN"
    assert win_mem.mistake_category is None
    assert "successfully" in win_mem.root_cause

    # 2. Lệnh BREAKEVEN
    be_data = {
        "id": 99905,
        "symbol": "XAUUSD",
        "order_type": "SELL",
        "entry_price": 2650.0,
        "exit_price": 2650.0,
        "stop_loss": 2650.0,
        "take_profit": 2610.0,
        "realized_pnl": 0.0,
        "close_reason": "BREAKEVEN",
        "open_time": (now - timedelta(minutes=45)).isoformat(),
        "close_time": now.isoformat(),
        "is_test": True,
    }
    be_mem = await reflexion_service.analyze_closed_order(be_data)
    assert be_mem.outcome == "BREAKEVEN"
    assert be_mem.mistake_category is None
    assert "Breakeven" in be_mem.lesson_learned or "breakeven" in be_mem.rule_to_add.lower()


@pytest.mark.anyio
async def test_reflexion_semantic_search_and_retrieval():
    """Kiểm tra tìm kiếm semantic search bài học tương tự bằng pgvector"""
    # Tạo sẵn 1 ký ức về SL quá ngắn
    now = datetime.now(timezone.utc)
    order_data = {
        "id": 99906,
        "symbol": "XAUUSD",
        "order_type": "BUY",
        "entry_price": 2655.0,
        "exit_price": 2645.0,
        "stop_loss": 2644.0,
        "take_profit": 2680.0,
        "realized_pnl": -35.0,
        "close_reason": "SL_HIT",
        "open_time": (now - timedelta(minutes=20)).isoformat(),
        "close_time": now.isoformat(),
        "is_test": True,
    }
    await reflexion_service.analyze_closed_order(order_data)

    # Tìm kiếm với câu hỏi bằng ngôn ngữ tự nhiên
    query = "Why did price wick out Stop Loss before flying to Take Profit?"
    matches = await reflexion_service.search_similar_lessons(
        query=query,
        mistake_category="SL_TOO_TIGHT",
        top_k=2,
        include_test=True,
    )

    assert len(matches) >= 1
    top_match = matches[0]
    assert top_match["mistake_category"] == "SL_TOO_TIGHT"
    assert top_match["similarity"] > 0.05


@pytest.mark.anyio
async def test_reflexion_api_endpoints():
    """Kiểm tra các REST API endpoints của Reflexion Engine"""
    # 1. Tạo 1 lệnh trong DB để test API analyze
    async with session_factory() as session:
        test_order = SimulatedOrder(
            symbol="XAUUSD",
            order_type="BUY",
            status="CLOSED",
            lot_size=Decimal("0.10"),
            entry_price=Decimal("2650.00"),
            exit_price=Decimal("2638.00"),
            stop_loss=Decimal("2638.00"),  # SL 12 points
            take_profit=Decimal("2680.00"),
            realized_pnl=Decimal("-36.00"),
            close_reason="SL_HIT",
            is_test=True,
            open_time=datetime.now(timezone.utc) - timedelta(minutes=15),
            close_time=datetime.now(timezone.utc),
        )
        session.add(test_order)
        await session.commit()
        await session.refresh(test_order)
        order_id = test_order.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. POST /api/v1/reflexion/analyze/{order_id}
        res_analyze = await client.post(f"/api/v1/reflexion/analyze/{order_id}")
        assert res_analyze.status_code == 200
        mem_data = res_analyze.json()
        assert mem_data["order_id"] == order_id
        assert mem_data["outcome"] == "LOSS"
        assert mem_data["mistake_category"] == "SL_TOO_TIGHT"

        # 2. GET /api/v1/reflexion/memories?include_test=true
        res_memories = await client.get("/api/v1/reflexion/memories?include_test=true")
        assert res_memories.status_code == 200
        records = res_memories.json()
        assert len(records) >= 1
        assert any(r["order_id"] == order_id for r in records)

        # 3. GET /api/v1/reflexion/search?query=...&include_test=true
        res_search = await client.get(
            "/api/v1/reflexion/search",
            params={"query": "Stop loss placed too tight", "include_test": True},
        )
        assert res_search.status_code == 200
        search_res = res_search.json()
        assert len(search_res) >= 1
        assert "similarity" in search_res[0]

        # 4. GET /api/v1/reflexion/stats?include_test=true
        res_stats = await client.get("/api/v1/reflexion/stats?include_test=true")
        assert res_stats.status_code == 200
        stats = res_stats.json()
        assert stats["total_memories"] >= 1
        assert "LOSS" in stats["outcomes"]
