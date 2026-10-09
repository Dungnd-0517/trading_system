from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import SimulatedOrder, SimulationAccount
from simulation.paper_worker import paper_worker

router = APIRouter()


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    order_type: Literal["BUY", "SELL"]
    lot_size: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    entry_price: Decimal | None = Field(default=None, max_digits=12, decimal_places=4)
    stop_loss: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    take_profit: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    strategy_trigger: str | None = Field(default=None, max_length=64)


class CloseOrderRequest(BaseModel):
    reason: str = Field(default="MANUAL_CLOSE", max_length=32)


@router.get("")
async def list_orders(
    limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[dict[str, object]]:
    rows = (
        await session.scalars(
            select(SimulatedOrder).order_by(SimulatedOrder.open_time.desc()).limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "ticket_uuid": str(row.ticket_uuid),
            "symbol": row.symbol,
            "order_type": row.order_type,
            "status": row.status,
            "lot_size": float(row.lot_size),
            "entry_price": float(row.entry_price),
            "exit_price": float(row.exit_price) if row.exit_price is not None else None,
            "stop_loss": float(row.stop_loss),
            "take_profit": float(row.take_profit),
            "slippage": float(row.slippage or 0.0),
            "commission": float(row.commission or 0.0),
            "swap": float(row.swap or 0.0),
            "close_reason": row.close_reason,
            "open_time": row.open_time.isoformat(),
            "close_time": row.close_time.isoformat() if row.close_time else None,
            "realized_pnl": float(row.realized_pnl) if row.realized_pnl is not None else None,
            "pnl_percentage": (
                float(row.pnl_percentage)
                if row.pnl_percentage is not None
                else (
                    round(
                        ((float(row.exit_price) - float(row.entry_price)) / float(row.entry_price))
                        * 100
                        * (1 if row.order_type == "BUY" else -1),
                        2,
                    )
                    if row.exit_price is not None and row.entry_price
                    else None
                )
            ),
            "strategy_trigger": row.strategy_trigger,
        }
        for row in rows
    ]


@router.post("", status_code=201)
async def create_order(request: OrderRequest) -> dict[str, object]:
    symbol = request.symbol.upper()
    is_buy = request.order_type == "BUY"

    quote: tuple[float, float] | None = None
    if request.entry_price is not None:
        p = float(request.entry_price)
        quote = (p, p)
        entry_val = p
    else:
        q = paper_worker.latest_quotes.get(symbol, {"bid": 2685.0, "ask": 2685.2})
        entry_val = q["ask"] if is_buy else q["bid"]

    if (is_buy and not float(request.stop_loss) < entry_val < float(request.take_profit)) or (
        not is_buy and not float(request.take_profit) < entry_val < float(request.stop_loss)
    ):
        raise HTTPException(status_code=422, detail="Prices must be ordered entry/SL/TP for the side")

    try:
        result = await paper_worker.open_order(
            symbol=symbol,
            side=request.order_type,
            lots=float(request.lot_size),
            stop_loss=float(request.stop_loss),
            take_profit=float(request.take_profit),
            strategy_trigger=request.strategy_trigger,
            quote=quote,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{order_id}/close")
async def close_order(
    order_id: int, request: CloseOrderRequest | None = None
) -> dict[str, object]:
    reason = request.reason if request else "MANUAL_CLOSE"
    try:
        closed = await paper_worker.close_order(order_id, reason=reason)
        return closed
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class PartialCloseRequest(BaseModel):
    ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    reason: str = Field(default="MANUAL_PARTIAL_TP", max_length=32)


@router.post("/{order_id}/partial-close")
async def partial_close_order_endpoint(
    order_id: int, request: PartialCloseRequest | None = None
) -> dict[str, object]:
    ratio = request.ratio if request else 0.5
    reason = request.reason if request else "MANUAL_PARTIAL_TP"
    try:
        updated = await paper_worker.partial_close_order(order_id, ratio=ratio, reason=reason)
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/account")
async def get_order_account(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    account = await session.scalar(select(SimulationAccount).where(SimulationAccount.id == 1))
    open_count = await session.scalar(
        select(func.count()).select_from(SimulatedOrder).where(SimulatedOrder.status.in_(["OPEN", "FILLED"]))
    ) or 0

    if not account:
        return {
            "initial_balance": 10000.00,
            "current_balance": 10000.00,
            "equity": 10000.00,
            "margin_used": 0.00,
            "free_margin": 10000.00,
            "open_positions_count": open_count,
        }

    balance = float(account.current_balance)
    equity = float(account.equity)
    margin = float(account.margin_used)
    return {
        "initial_balance": float(account.initial_balance),
        "current_balance": balance,
        "equity": equity,
        "margin_used": margin,
        "free_margin": equity - margin,
        "open_positions_count": open_count,
    }