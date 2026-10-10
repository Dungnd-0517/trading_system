from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.models import SimulatedOrder, SimulationAccount

router = APIRouter()


@router.get("/account")
async def get_simulation_account(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    account = await session.scalar(select(SimulationAccount).where(SimulationAccount.id == 1))
    open_count = await session.scalar(
        select(func.count())
        .select_from(SimulatedOrder)
        .where(SimulatedOrder.status.in_(["OPEN", "FILLED"]), SimulatedOrder.is_test.is_(False))
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
