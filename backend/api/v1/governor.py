from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.strategy_governor import (
    AgentParamAdjustment,
    ConsensusReport,
    strategy_governor,
    validate_and_apply_hard_guardrails,
)
from core.database import get_session

router = APIRouter()


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


@router.get("/consensus", response_model=ConsensusReport)
async def get_governor_consensus(
    include_test: bool = Query(False, description="Bao gồm dữ liệu test"),
    session: AsyncSession = Depends(get_session),
):
    """
    Lấy báo cáo đồng thuận (Consensus Report) mới nhất từ Hội đồng 4 Agents:
    News & Event Agent, Technical RAG Agent, Reflexion Agent và Strategy Governor.
    """
    try:
        report = await strategy_governor.synthesize_consensus(
            session, include_test=include_test
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize consensus: {exc}")


@router.get("/runtime-params", response_model=dict[str, Any])
async def get_runtime_params():
    """
    Lấy bộ tham số vận hành hiện tại từ Redis Cache (Fast Execution Engine) hoặc DB.
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
            session, include_test=include_test
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
        # 1. Đọc tham số hiện tại
        current = await strategy_governor.get_current_runtime_params()

        # 2. Ghi đè các trường được chỉ định
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

        # 3. Tính drawdown ngày và chạy qua Hard Guardrails
        daily_dd = await strategy_governor.calculate_daily_drawdown(session)
        validated, was_hard_breached = validate_and_apply_hard_guardrails(
            proposed, current_daily_drawdown=daily_dd
        )

        # 4. Đồng bộ DB và Redis
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
