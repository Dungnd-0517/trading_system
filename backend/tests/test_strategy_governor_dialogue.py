from datetime import datetime, time, timezone
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from ai_engine.strategy_governor import (
    AgentParamAdjustment,
    strategy_governor,
    validate_and_apply_hard_guardrails,
)
from core.database import session_factory
from core.models import (
    AgentDecisionLog,
    AgentTraderDialogue,
    SimulatedOrder,
    SimulationAccount,
    SystemTradingConfig,
)
from main import app


@pytest.mark.anyio
async def test_governor_intent_parsing_and_valid_overrides():
    """
    Kiểm tra Governor phân tích ý định từ Trader và thực thi thành công
    các lệnh nằm trong ngưỡng an toàn của Hard Guardrails (D21/D24).
    """
    async with session_factory() as session:
        # 1. Chỉ thị hạ rủi ro xuống 0.5% và nới SL lên 2.0x ATR
        msg1 = "Hạ mức rủi ro xuống 0.5% và nới SL lên 2.0x ATR"
        res1 = await strategy_governor.process_trader_dialogue(
            message=msg1, session=session, is_test=True
        )
        assert res1["guardrail_passed"] is True
        assert res1["actions_taken"]["risk_per_trade_percent"] == 0.50
        assert res1["actions_taken"]["atr_sl_multiplier"] == 2.00
        assert "THÀNH CÔNG" in res1["response"]

        # Kiểm tra tham số đã được đồng bộ
        current_params = await strategy_governor.get_current_runtime_params()
        assert current_params["risk_per_trade_percent"] == 0.50
        assert current_params["atr_sl_multiplier"] == 2.00

        # 2. Chỉ thị tạm dừng giao dịch
        msg2 = "Tạm dừng giao dịch để theo dõi tin tức"
        res2 = await strategy_governor.process_trader_dialogue(
            message=msg2, session=session, is_test=True
        )
        assert res2["guardrail_passed"] is True
        assert res2["actions_taken"]["trading_allowed"] is False

        current_params2 = await strategy_governor.get_current_runtime_params()
        assert current_params2["trading_allowed"] is False
        assert "Tạm dừng" in current_params2["halt_reason"]

        # 3. Chỉ thị tiếp tục giao dịch
        msg3 = "Tiếp tục giao dịch"
        res3 = await strategy_governor.process_trader_dialogue(
            message=msg3, session=session, is_test=True
        )
        assert res3["guardrail_passed"] is True
        assert res3["actions_taken"]["trading_allowed"] is True

        current_params3 = await strategy_governor.get_current_runtime_params()
        assert current_params3["trading_allowed"] is True
        assert current_params3["halt_reason"] is None


@pytest.mark.anyio
async def test_governor_hard_guardrails_rejection_of_excessive_risk():
    """
    Kiểm tra Governor kiên quyết TỪ CHỐI chỉ thị vi phạm Hard Limits (rủi ro > 1.50% hoặc < 0.25%).
    Giải thích nguyên tắc bảo toàn vốn và không sửa đổi cấu hình hệ thống.
    """
    async with session_factory() as session:
        # Lấy tham số ban đầu
        initial_params = await strategy_governor.get_current_runtime_params()

        # Trader yêu cầu đặt rủi ro 5.0%
        msg = "Đặt rủi ro 5.0% gỡ lỗ nhanh"
        res = await strategy_governor.process_trader_dialogue(
            message=msg, session=session, is_test=True
        )

        # Rào chắn cứng phải chặn lại
        assert res["guardrail_passed"] is False
        assert "Từ chối" in res["response"]
        assert "1.50%" in res["response"]
        assert "0.25%" in res["response"]
        assert "Bảo toàn Vốn" in res["response"]

        # Tham số trong hệ thống KHÔNG được phép đổi thành 5.0%
        current_params = await strategy_governor.get_current_runtime_params()
        assert current_params["risk_per_trade_percent"] != 5.0
        assert current_params["risk_per_trade_percent"] == initial_params["risk_per_trade_percent"]


@pytest.mark.anyio
async def test_governor_hard_guardrails_rejection_under_high_drawdown():
    """
    Kiểm tra Governor từ chối mở lại giao dịch nếu drawdown ngày >= 3.0%
    (Max Daily Drawdown Breaker khóa cứng).
    """
    async with session_factory() as session:
        now = datetime.now(timezone.utc)
        # Tạo 1 lệnh lỗ nặng 350 USD (3.5% của tài khoản 10,000 USD)
        loss_order = SimulatedOrder(
            symbol="XAUUSD",
            order_type="BUY",
            lot_size=Decimal("0.5"),
            entry_price=Decimal("4180.0"),
            exit_price=Decimal("4173.0"),
            stop_loss=Decimal("4173.0"),
            take_profit=Decimal("4200.0"),
            realized_pnl=Decimal("-350.00"),
            status="CLOSED",
            open_time=now,
            close_time=now,
            is_test=True,
        )
        session.add(loss_order)
        await session.commit()

        # Kiểm tra drawdown ngày >= 3.0%
        dd = await strategy_governor.calculate_daily_drawdown(session, include_test=True)
        assert dd >= 3.00

        # Trader cố mở lại giao dịch
        msg = "Mở lại giao dịch"
        res = await strategy_governor.process_trader_dialogue(
            message=msg, session=session, is_test=True
        )
        assert res["guardrail_passed"] is False
        assert "Max Daily Drawdown Breaker" in res["response"]


@pytest.mark.anyio
async def test_governor_executive_briefing_generation():
    """
    Kiểm tra Governor xuất bản Executive Briefing:
    - Tổng hợp thông tin từ 3 Agents (News, Technical RAG, Reflexion).
    - Lưu bản ghi vào agent_trader_dialogue với message_type = 'BRIEFING'.
    - Tạo cấu trúc dữ liệu đầy đủ.
    """
    async with session_factory() as session:
        briefing = await strategy_governor.generate_executive_briefing(
            session=session, include_test=True, is_test=True
        )

        assert briefing["dialogue_id"] is not None
        assert "BẢN TIN ĐIỀU HÀNH CHIẾN LƯỢC" in briefing["briefing_text"]
        assert "News & Event Agent" in briefing["briefing_text"]
        assert "Technical RAG Agent" in briefing["briefing_text"]
        assert "Reflexion Agent" in briefing["briefing_text"]
        assert "Governor Mandate" in briefing["briefing_text"]
        assert "active_params" in briefing

        # Kiểm tra trong DB
        dialogue = await session.get(AgentTraderDialogue, briefing["dialogue_id"])
        assert dialogue is not None
        assert dialogue.sender == "GOVERNOR"
        assert dialogue.message_type == "BRIEFING"
        assert dialogue.is_test is True


@pytest.mark.anyio
async def test_governor_respond_trade_approval():
    """
    Kiểm tra xử lý phê duyệt (APPROVE) và từ chối (REJECT) từ Trader.
    """
    async with session_factory() as session:
        # Tạo yêu cầu phê duyệt mẫu
        approval_req = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="APPROVAL_REQUEST",
            content="Đề xuất BUY 0.20 lots XAUUSD tại 4184.50 (SL: 4178.90, TP: 4197.50, RR: 2.3).",
            metadata_={"action": "BUY", "entry": 4184.50, "sl": 4178.90, "tp": 4197.50},
            approval_status="PENDING",
            is_test=True,
        )
        session.add(approval_req)
        await session.commit()
        await session.refresh(approval_req)

        # Phê duyệt lệnh
        res_approve = await strategy_governor.respond_trade_approval(
            dialogue_id=approval_req.id,
            action="APPROVE",
            session=session,
            is_test=True,
        )
        assert res_approve["status"] == "APPROVED"
        assert "PHÊ DUYỆT" in res_approve["message"]

        # Kiểm tra trạng thái DB
        await session.refresh(approval_req)
        assert approval_req.approval_status == "APPROVED"

        # Tạo yêu cầu thứ 2 để test REJECT
        reject_req = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="APPROVAL_REQUEST",
            content="Đề xuất SELL 0.15 lots XAUUSD tại 4182.00.",
            metadata_={},
            approval_status="PENDING",
            is_test=True,
        )
        session.add(reject_req)
        await session.commit()
        await session.refresh(reject_req)

        res_reject = await strategy_governor.respond_trade_approval(
            dialogue_id=reject_req.id,
            action="REJECT",
            session=session,
            is_test=True,
        )
        assert res_reject["status"] == "REJECTED"
        assert "TỪ CHỐI" in res_reject["message"]


@pytest.mark.anyio
async def test_governor_dialogue_history_retrieval():
    """
    Kiểm tra truy vấn lịch sử đối thoại giữa Trader và Governor.
    """
    async with session_factory() as session:
        d1 = AgentTraderDialogue(
            sender="TRADER",
            message_type="TEXT",
            content="TEST D18 Msg 1",
            metadata_={},
            is_test=True,
        )
        d2 = AgentTraderDialogue(
            sender="GOVERNOR",
            message_type="TEXT",
            content="TEST D18 Msg 2",
            metadata_={},
            is_test=True,
        )
        session.add_all([d1, d2])
        await session.commit()

        history = await strategy_governor.get_dialogue_history(
            session=session, limit=10, include_test=True
        )
        contents = [h["content"] for h in history]
        assert "TEST D18 Msg 1" in contents
        assert "TEST D18 Msg 2" in contents


@pytest.mark.anyio
async def test_governor_rest_api_endpoints():
    """
    Kiểm tra tích hợp toàn diện REST API router /api/v1/agents/governor/*
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /briefing
        briefing_resp = await client.get("/api/v1/agents/governor/briefing?include_test=true")
        assert briefing_resp.status_code == 200
        briefing_data = briefing_resp.json()
        assert "headline" in briefing_data
        assert "briefing_text" in briefing_data

        # 2. POST /dialogue (Lệnh hợp lệ)
        dialogue_resp1 = await client.post(
            "/api/v1/agents/governor/dialogue",
            json={"message": "Hạ mức rủi ro xuống 0.75%", "is_test": True},
        )
        assert dialogue_resp1.status_code == 200
        d1_data = dialogue_resp1.json()
        assert d1_data["guardrail_passed"] is True
        assert d1_data["actions_taken"]["risk_per_trade_percent"] == 0.75

        # 3. POST /dialogue (Lệnh vi phạm 5%)
        dialogue_resp2 = await client.post(
            "/api/v1/agents/governor/dialogue",
            json={"message": "Đặt rủi ro 5.0% gỡ lỗ", "is_test": True},
        )
        assert dialogue_resp2.status_code == 200
        d2_data = dialogue_resp2.json()
        assert d2_data["guardrail_passed"] is False
        assert "Từ chối" in d2_data["response"]

        # 4. GET /dialogue/history
        hist_resp = await client.get("/api/v1/agents/governor/dialogue/history?include_test=true")
        assert hist_resp.status_code == 200
        assert isinstance(hist_resp.json(), list)

        # 5. GET /consensus
        consensus_resp = await client.get("/api/v1/agents/governor/consensus?include_test=true")
        assert consensus_resp.status_code == 200
        assert "market_regime" in consensus_resp.json()

        # 6. GET /runtime-params
        params_resp = await client.get("/api/v1/agents/governor/runtime-params")
        assert params_resp.status_code == 200
        assert "risk_per_trade_percent" in params_resp.json()
