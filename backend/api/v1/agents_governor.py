from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.strategy_governor import (
    AgentParamAdjustment,
    ConsensusReport,
    ExecutiveBriefingResponse,
    TraderDialogueResponse,
    strategy_governor,
    validate_and_apply_hard_guardrails,
)
from core.database import get_session

router = APIRouter()


class DialogueRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Tin nhắn hoặc chỉ thị gửi tới Strategy Governor")
    is_test: bool = Field(False, description="Cờ môi trường kiểm thử D18")


class ApprovalResponseRequest(BaseModel):
    dialogue_id: int = Field(..., description="ID của bản ghi yêu cầu phê duyệt trong agent_trader_dialogue")
    action: str = Field(..., description="'APPROVE' hoặc 'REJECT'")
    is_test: bool = Field(False, description="Cờ môi trường kiểm thử D18")


class ManualOverrideRequest(BaseModel):
    risk_per_trade_percent: float | None = Field(None, ge=0.25, le=1.50)
    min_risk_reward_ratio: float | None = Field(None, ge=1.20, le=4.00)
    atr_sl_multiplier: float | None = Field(None, ge=1.00, le=3.00)
    trading_allowed: bool | None = None
    halt_reason: str | None = None


class OverrideResponse(BaseModel):
    status: str
    message: str
    active_params: AgentParamAdjustment
    was_hard_breached: bool


@router.get("/briefing", response_model=ExecutiveBriefingResponse)
async def get_executive_briefing(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    session: AsyncSession = Depends(get_session),
):
    """
    Xuất bản bản tin điều hành chiến lược (Executive Briefing) tức thời:
    Tổng hợp toàn diện từ News Agent (vĩ mô), Technical RAG (cấu trúc nến, hợp lưu đa trường phái),
    Reflexion Agent (bài học kiểm điểm) và chỉ thị rủi ro hiện hành từ CRO Strategy Governor.
    """
    try:
        res = await strategy_governor.generate_executive_briefing(
            session=session, include_test=include_test, is_test=include_test
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate executive briefing: {exc}")


@router.post("/dialogue", response_model=TraderDialogueResponse)
async def send_trader_dialogue(
    payload: DialogueRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Kênh đối thoại hai chiều Trader - Governor:
    - Tiếp nhận câu hỏi, tin nhắn trao đổi hoặc câu lệnh ghi đè (rủi ro, dừng/mở giao dịch, nới SL, briefing).
    - Thẩm định nghiêm ngặt qua Bộ Rào chắn Cứng (Hard Guardrails D21/D24).
    - Nếu yêu cầu vượt giới hạn (ví dụ rủi ro > 1.5% hoặc drawdown >= 3%), Governor kiên quyết từ chối giải thích lý do bảo vệ vốn.
    """
    try:
        res = await strategy_governor.process_trader_dialogue(
            message=payload.message,
            session=session,
            is_test=payload.is_test,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process trader dialogue: {exc}")


@router.post("/respond-approval")
async def respond_trade_approval(
    payload: ApprovalResponseRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Xử lý phản hồi phê duyệt (APPROVE) hoặc từ chối (REJECT) từ Trader đối với một đề xuất mở lệnh.
    """
    try:
        res = await strategy_governor.respond_trade_approval(
            dialogue_id=payload.dialogue_id,
            action=payload.action,
            session=session,
            is_test=payload.is_test,
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to respond to trade approval: {exc}")


@router.get("/dialogue/history", response_model=list[dict[str, Any]])
async def get_dialogue_history(
    limit: int = Query(50, ge=1, le=200, description="Số lượng tin nhắn tối đa"),
    include_test: bool = Query(False, description="Bao gồm tin nhắn test D18"),
    session: AsyncSession = Depends(get_session),
):
    """
    Truy vấn lịch sử đối thoại giữa Chủ thể và Strategy Governor phục vụ Cockpit Studio Vue 3.
    """
    try:
        history = await strategy_governor.get_dialogue_history(
            session=session, limit=limit, include_test=include_test
        )
        return history
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dialogue history: {exc}")


@router.get("/consensus", response_model=ConsensusReport)
async def get_governor_consensus(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy báo cáo đồng thuận (Consensus Report) mới nhất từ Hội đồng 4 Agents.
    """
    try:
        report = await strategy_governor.synthesize_consensus(
            session, include_test=include_test, is_test=include_test
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize consensus: {exc}")


@router.get("/runtime-params", response_model=dict[str, Any])
async def get_runtime_params():
    """
    Lấy bộ tham số vận hành hiện tại từ Redis Cache hoặc DB.
    """
    try:
        params = await strategy_governor.get_current_runtime_params()
        return params
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch runtime params: {exc}")


@router.post("/evaluate", response_model=ConsensusReport)
async def evaluate_now(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    session: AsyncSession = Depends(get_session),
):
    """
    Kích hoạt đánh giá tức thì đồng thuận thị trường và cập nhật bộ tham số vận hành.
    """
    try:
        report = await strategy_governor.synthesize_consensus(
            session, include_test=include_test, is_test=include_test
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate governor: {exc}")


@router.post("/override", response_model=OverrideResponse)
async def manual_override_params(
    request: ManualOverrideRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Can thiệp thủ công từ Trader (Override) có bảo vệ bởi Bộ Rào chắn Cứng (Hard Guardrails):
    Bất kể can thiệp gì, nếu drawdown ngày >= 3%, quyền giao dịch vẫn bị khóa cứng.
    """
    try:
        current = await strategy_governor.get_current_runtime_params()
        proposed = dict(current)
        if request.risk_per_trade_percent is not None:
            proposed["risk_per_trade_percent"] = request.risk_per_trade_percent
        if request.min_risk_reward_ratio is not None:
            proposed["min_risk_reward_ratio"] = request.min_risk_reward_ratio
        if request.atr_sl_multiplier is not None:
            proposed["atr_sl_multiplier"] = request.atr_sl_multiplier
        if request.trading_allowed is not None:
            proposed["trading_allowed"] = request.trading_allowed
        if request.halt_reason is not None:
            proposed["halt_reason"] = request.halt_reason
        proposed["updated_by_agent"] = "MANUAL_TRADER_OVERRIDE"

        daily_dd = await strategy_governor.calculate_daily_drawdown(session)
        validated, was_hard_breached = validate_and_apply_hard_guardrails(
            proposed, current_daily_drawdown=daily_dd
        )

        await strategy_governor._persist_and_sync_cache(session, validated)

        msg = (
            "Ghi đè tham số thành công"
            if not was_hard_breached
            else "Cảnh báo: Hard Drawdown Breaker 3% đã cưỡng chế khóa giao dịch"
        )
        return {
            "status": "success" if not was_hard_breached else "warning",
            "message": msg,
            "active_params": validated,
            "was_hard_breached": was_hard_breached,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to override params: {exc}")
