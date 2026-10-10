from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.signal_worker import signal_worker
from core.database import get_session
from core.models import MarketCandle, StrategySignal, SystemTradingConfig
from simulation.auto_executor import auto_executor

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    execution_mode: Literal["MANUAL", "SEMI_AUTO", "FULL_AUTO"] | None = None
    risk_per_trade_percent: Decimal | None = Field(default=None, ge=Decimal("0.1"), le=Decimal("5.0"))
    breakeven_r_multiple: Decimal | None = Field(default=None, ge=Decimal("1.0"), le=Decimal("5.0"))
    enable_partial_tp: bool | None = None
    partial_tp_ratio: Decimal | None = Field(default=None, ge=Decimal("0.1"), le=Decimal("0.9"))
    partial_tp_r_multiple: Decimal | None = Field(default=None, ge=Decimal("1.0"), le=Decimal("5.0"))
    news_circuit_breaker_enabled: bool | None = None
    news_circuit_breaker_buffer_mins: int | None = Field(default=None, ge=5, le=120)
    max_open_positions: int | None = Field(default=None, ge=1, le=10)


class BacktestRequest(BaseModel):
    symbol: str = "XAUUSD"
    risk_pct: float = Field(default=1.0, ge=0.1, le=5.0)
    initial_balance: float = Field(default=10000.0, ge=1000.0)


@router.get("/signals")
async def list_signals(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    include_test: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    query = select(StrategySignal).order_by(StrategySignal.generated_at.desc()).limit(limit)
    if not include_test:
        query = query.where(StrategySignal.is_test.is_(False))
    if status:
        query = query.where(StrategySignal.status == status.upper())

    rows = (await session.scalars(query)).all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "side": row.side,
            "generated_at": row.generated_at.isoformat(),
            "session_name": row.session_name,
            "entry_price": float(row.entry_price),
            "stop_loss": float(row.stop_loss),
            "take_profit_1": float(row.take_profit_1),
            "take_profit_2": float(row.take_profit_2) if row.take_profit_2 else None,
            "risk_reward": float(row.risk_reward),
            "status": row.status,
            "invalidated_reason": row.invalidated_reason,
            "reason": row.reason,
            "executed_order_id": row.executed_order_id,
            "is_test": row.is_test,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/signals/evaluate")
async def trigger_signal_evaluation(
    symbol: str = Query(default="XAUUSD"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        signal_res = await signal_worker.evaluate_signal(symbol, session)
        if not signal_res:
            return {
                "status": "NO_SETUP",
                "message": "Không phát hiện setup SMC hợp lệ tại nến hiện tại hoặc ngoài phiên Kill Zone.",
            }

        return {
            "status": signal_res.status,
            "signal": {
                "id": signal_res.id,
                "symbol": signal_res.symbol,
                "side": signal_res.side,
                "entry_price": float(signal_res.entry_price),
                "stop_loss": float(signal_res.stop_loss),
                "take_profit_1": float(signal_res.take_profit_1),
                "take_profit_2": float(signal_res.take_profit_2) if signal_res.take_profit_2 else None,
                "risk_reward": float(signal_res.risk_reward),
                "session_name": signal_res.session_name,
                "reason": signal_res.reason,
                "invalidated_reason": signal_res.invalidated_reason,
            },
        }
    except Exception as exc:
        logger.exception("Error evaluating signals for %s: %s", symbol, exc)
        return {
            "status": "ERROR",
            "message": f"Lỗi khi đánh giá tín hiệu SMC: {str(exc)}",
        }


@router.post("/signals/{signal_id}/execute")
async def execute_signal_endpoint(
    signal_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        res = await auto_executor.execute_signal(signal_id, session=session, force_manual=True)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/config")
async def get_trading_config(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
    if not cfg:
        cfg = SystemTradingConfig(id=1)
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)

    return {
        "execution_mode": cfg.execution_mode,
        "risk_per_trade_percent": float(cfg.risk_per_trade_percent),
        "breakeven_r_multiple": float(cfg.breakeven_r_multiple),
        "enable_partial_tp": cfg.enable_partial_tp,
        "partial_tp_ratio": float(cfg.partial_tp_ratio),
        "partial_tp_r_multiple": float(cfg.partial_tp_r_multiple),
        "news_circuit_breaker_enabled": cfg.news_circuit_breaker_enabled,
        "news_circuit_breaker_buffer_mins": cfg.news_circuit_breaker_buffer_mins,
        "max_open_positions": cfg.max_open_positions,
        "updated_at": cfg.updated_at.isoformat(),
    }


@router.put("/config")
async def update_trading_config(
    request: ConfigUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
    if not cfg:
        cfg = SystemTradingConfig(id=1)
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)

    values = request.model_dump(exclude_unset=True)
    for k, v in values.items():
        setattr(cfg, k, v)

    cfg.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(cfg)

    return {
        "status": "success",
        "message": "Cập nhật cấu hình hệ thống thành công",
        "config": {
            "execution_mode": cfg.execution_mode,
            "risk_per_trade_percent": float(cfg.risk_per_trade_percent),
            "breakeven_r_multiple": float(cfg.breakeven_r_multiple),
            "enable_partial_tp": cfg.enable_partial_tp,
            "partial_tp_ratio": float(cfg.partial_tp_ratio),
            "news_circuit_breaker_enabled": cfg.news_circuit_breaker_enabled,
            "news_circuit_breaker_buffer_mins": cfg.news_circuit_breaker_buffer_mins,
            "max_open_positions": cfg.max_open_positions,
        },
    }


@router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Chạy mô phỏng kiểm thử lại chiến lược SMC trên nến lịch sử trong DB"""
    # 1. Lấy nến M15
    q_m15 = (
        select(MarketCandle)
        .where(MarketCandle.symbol == request.symbol, MarketCandle.timeframe == "M15")
        .order_by(MarketCandle.open_time.asc())
        .limit(1000)
    )
    candles = (await session.scalars(q_m15)).all()
    if len(candles) < 80:
        raise HTTPException(
            status_code=400,
            detail=f"Chưa đủ dữ liệu nến M15 để backtest (cần ít nhất 80 nến, hiện có {len(candles)} nến)",
        )

    # 2. Thuật toán mô phỏng trading
    trades = []
    balance = request.initial_balance
    peak_balance = balance
    max_drawdown_dollars = 0.0
    equity_curve = [{"time": candles[0].open_time.isoformat(), "balance": balance, "trade_no": 0}]

    i = 60
    while i < len(candles) - 10:
        c = candles[i]
        # Giả lập phát hiện setup: nến giảm mạnh sau đó rút chân tạo cơ hội Buy hoặc ngược lại
        c_prev = candles[i - 1]
        rng = float(c.high) - float(c.low)
        atr_approx = max(rng, 1.5)

        # Mô phỏng quy tắc SMC: Buy khi nến M15 rút chân ở hỗ trợ
        is_buy_setup = float(c.close) > float(c.open) and (float(c.open) - float(c.low)) > 0.4 * rng
        is_sell_setup = float(c.close) < float(c.open) and (float(c.high) - float(c.open)) > 0.4 * rng

        if is_buy_setup or is_sell_setup:
            side = "BUY" if is_buy_setup else "SELL"
            entry = float(c.close)
            sl_dist = round(atr_approx * 1.5, 2)
            tp_dist = round(sl_dist * 2.2, 2)  # R:R = 1:2.2

            sl = entry - sl_dist if side == "BUY" else entry + sl_dist
            tp = entry + tp_dist if side == "BUY" else entry - tp_dist

            risk_amount = balance * (request.risk_pct / 100.0)
            lots = max(0.01, min(5.0, round(risk_amount / (sl_dist * 100.0), 2)))

            # Quét các nến tương lai để xem chạm SL hay TP trước
            outcome = None
            exit_price = None
            exit_time = None

            for future_idx in range(i + 1, min(i + 40, len(candles))):
                fc = candles[future_idx]
                if side == "BUY":
                    if float(fc.low) <= sl:
                        outcome = "LOSS"
                        exit_price = sl
                        exit_time = fc.open_time
                        break
                    elif float(fc.high) >= tp:
                        outcome = "WIN"
                        exit_price = tp
                        exit_time = fc.open_time
                        break
                else:
                    if float(fc.high) >= sl:
                        outcome = "LOSS"
                        exit_price = sl
                        exit_time = fc.open_time
                        break
                    elif float(fc.low) <= tp:
                        outcome = "WIN"
                        exit_price = tp
                        exit_time = fc.open_time
                        break

            if outcome:
                direction = 1 if side == "BUY" else -1
                pnl = round((exit_price - entry) * direction * lots * 100.0, 2)
                balance += pnl
                if balance > peak_balance:
                    peak_balance = balance
                dd = peak_balance - balance
                if dd > max_drawdown_dollars:
                    max_drawdown_dollars = dd

                trade_record = {
                    "trade_no": len(trades) + 1,
                    "entry_time": c.open_time.isoformat(),
                    "exit_time": exit_time.isoformat() if exit_time else None,
                    "side": side,
                    "lots": lots,
                    "entry_price": entry,
                    "exit_price": exit_price,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "outcome": outcome,
                    "pnl": pnl,
                    "balance_after": round(balance, 2),
                }
                trades.append(trade_record)
                equity_curve.append(
                    {
                        "time": exit_time.isoformat() if exit_time else c.open_time.isoformat(),
                        "balance": round(balance, 2),
                        "trade_no": len(trades),
                    }
                )
                i = future_idx + 1
                continue

        i += 1

    total_trades = len(trades)
    win_trades = sum(1 for t in trades if t["outcome"] == "WIN")
    loss_trades = total_trades - win_trades
    winrate = round((win_trades / total_trades) * 100, 2) if total_trades > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    net_pnl = round(balance - request.initial_balance, 2)
    max_dd_pct = round((max_drawdown_dollars / peak_balance) * 100, 2) if peak_balance > 0 else 0.0

    return {
        "summary": {
            "initial_balance": request.initial_balance,
            "final_balance": round(balance, 2),
            "net_pnl": net_pnl,
            "net_pnl_percent": round((net_pnl / request.initial_balance) * 100, 2),
            "total_trades": total_trades,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "winrate_percent": winrate,
            "profit_factor": profit_factor,
            "max_drawdown_percent": max_dd_pct,
            "max_drawdown_dollars": round(max_drawdown_dollars, 2),
        },
        "equity_curve": equity_curve,
        "trades": trades,
    }
