from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import SimulatedOrder

router = APIRouter()


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    order_type: Literal["BUY", "SELL"]
    lot_size: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    entry_price: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    stop_loss: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    take_profit: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    strategy_trigger: str | None = Field(default=None, max_length=64)


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
            "symbol": row.symbol,
            "order_type": row.order_type,
            "status": row.status,
            "lot_size": float(row.lot_size),
            "entry_price": float(row.entry_price),
            "stop_loss": float(row.stop_loss),
            "take_profit": float(row.take_profit),
            "open_time": row.open_time.isoformat(),
            "realized_pnl": float(row.realized_pnl) if row.realized_pnl is not None else None,
        }
        for row in rows
    ]


@router.post("", status_code=201)
async def create_order(
    request: OrderRequest, session: AsyncSession = Depends(get_session)
) -> dict[str, object]:
    is_buy = request.order_type == "BUY"
    if (is_buy and not request.stop_loss < request.entry_price < request.take_profit) or (
        not is_buy and not request.take_profit < request.entry_price < request.stop_loss
    ):
        raise HTTPException(status_code=422, detail="Prices must be ordered entry/SL/TP for the side")

    order = SimulatedOrder(
        symbol=request.symbol.upper(),
        order_type=request.order_type,
        status="FILLED",
        lot_size=request.lot_size,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        open_time=datetime.now(timezone.utc),
        strategy_trigger=request.strategy_trigger,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return {"id": order.id, "status": order.status, "open_time": order.open_time.isoformat()}