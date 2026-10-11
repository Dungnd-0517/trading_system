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
    timeframe: str = Field(default="M15", description="Khung thời gian nến (M1, M5, M15, H1, H4, D1)")
    bars_count: int = Field(default=500, ge=50, le=5000, description="Số lượng nến kiểm thử")
    initial_balance: float = Field(default=10000.0, ge=100.0, description="Vốn khởi tạo ban đầu ($)")
    risk_pct: float = Field(default=1.0, ge=0.1, le=5.0, description="Tỷ lệ rủi ro mỗi lệnh (%)")
    sizing_mode: str = Field(default="FIXED", description="Cách tính rủi ro: FIXED (% trên vốn ban đầu) hoặc COMPOUND (% trên vốn lũy kế)")
    atr_period: int = Field(default=14, ge=3, le=50, description="Chu kỳ tính Average True Range")
    atr_sl_multiplier: float = Field(default=1.5, ge=0.5, le=4.0, description="Hệ số ATR cho khoảng cách Stop Loss")
    risk_reward_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="Tỷ lệ Risk:Reward kỳ vọng (TP / SL)")
    enable_breakeven: bool = Field(default=True, description="Tự động dời SL về Entry khi giá chạy được >= 1.5R")
    enable_partial_tp: bool = Field(default=False, description="Chốt lời 50% khối lượng khi đạt 1.5R")
    session_filter: str = Field(default="ALL", description="Lọc phiên: ALL hoặc KILL_ZONES_ONLY")



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


def format_duration(seconds: float) -> str:
    total_mins = int(seconds // 60)
    if total_mins < 60:
        return f"{total_mins}m"
    hours = total_mins // 60
    mins = total_mins % 60
    if hours < 24:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    days = hours // 24
    rem_hours = hours % 24
    return f"{days}d {rem_hours}h" if rem_hours else f"{days}d"


def is_in_kill_zone(dt_utc) -> bool:
    """London: 14:00-17:00 ICT (07:00-10:00 UTC), NY AM: 19:00-22:00 ICT (12:00-15:00 UTC)"""
    hour_utc = dt_utc.hour
    return (7 <= hour_utc < 10) or (12 <= hour_utc < 15)


@router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Chạy mô phỏng kiểm thử lại chiến lược SMC trên nến lịch sử trong DB với đầy đủ tham số và quản trị rủi ro"""
    tf = request.timeframe.upper()

    # 1. Lấy nến theo timeframe và bars_count (lấy các nến gần nhất rồi đảo ngược theo thời gian tăng dần)
    q = (
        select(MarketCandle)
        .where(MarketCandle.symbol == request.symbol, MarketCandle.timeframe == tf)
        .order_by(MarketCandle.open_time.desc())
        .limit(request.bars_count)
    )
    candles = list(reversed((await session.scalars(q)).all()))
    min_required = 30
    if len(candles) < min_required:
        raise HTTPException(
            status_code=400,
            detail=f"Chưa đủ dữ liệu nến {tf} để backtest (cần ít nhất {min_required} nến, hiện có {len(candles)} nến)",
        )

    # 2. Tính toán True Range & Rolling ATR chu kỳ (mặc định 14)
    n_candles = len(candles)
    tr_list = []
    for k in range(n_candles):
        c_k = candles[k]
        h = float(c_k.high)
        l = float(c_k.low)
        if k == 0:
            tr_list.append(h - l)
        else:
            prev_c = float(candles[k - 1].close)
            tr_list.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))

    atr_period = max(3, min(request.atr_period, 30))
    atr_values = []
    for k in range(n_candles):
        start_idx = max(0, k - atr_period + 1)
        sub_tr = tr_list[start_idx : k + 1]
        atr_values.append(sum(sub_tr) / len(sub_tr) if sub_tr else 1.5)

    # 3. Thuật toán mô phỏng trading
    trades = []
    balance = request.initial_balance
    peak_balance = balance
    max_drawdown_dollars = 0.0
    equity_curve = [{"time": candles[0].open_time.isoformat(), "balance": balance, "trade_no": 0}]

    i = atr_period
    while i < n_candles - 5:
        c = candles[i]
        c_time = c.open_time

        # Kiểm tra lọc phiên nếu bật KILL_ZONES_ONLY
        if request.session_filter == "KILL_ZONES_ONLY" and not is_in_kill_zone(c_time):
            i += 1
            continue

        rng = float(c.high) - float(c.low)
        if rng <= 0.2:
            i += 1
            continue

        lower_wick = float(c.open) - float(c.low) if float(c.close) >= float(c.open) else float(c.close) - float(c.low)
        upper_wick = float(c.high) - float(c.close) if float(c.close) >= float(c.open) else float(c.high) - float(c.open)

        # Mô phỏng quy tắc SMC: Quét thanh khoản & rút chân từ chối giá tại POI
        is_buy_setup = (
            lower_wick >= 0.35 * rng
            and float(c.close) > (float(c.high) + float(c.low)) / 2
        )
        is_sell_setup = (
            upper_wick >= 0.35 * rng
            and float(c.close) < (float(c.high) + float(c.low)) / 2
        )

        if is_buy_setup or is_sell_setup:
            side = "BUY" if is_buy_setup else "SELL"
            entry = float(c.close)
            current_atr = max(0.6, atr_values[i])
            sl_dist = round(max(0.6, current_atr * request.atr_sl_multiplier), 2)
            tp_dist = round(sl_dist * request.risk_reward_ratio, 2)

            sl = round(entry - sl_dist if side == "BUY" else entry + sl_dist, 2)
            tp = round(entry + tp_dist if side == "BUY" else entry - tp_dist, 2)

            # Tính toán vốn rủi ro và Lot size chính xác 1%
            if request.sizing_mode == "FIXED":
                risk_capital = request.initial_balance * (request.risk_pct / 100.0)
            else:
                risk_capital = balance * (request.risk_pct / 100.0)

            raw_lots = risk_capital / (sl_dist * 100.0)
            lots = max(0.01, min(20.0, round(raw_lots, 2)))
            expected_risk = round(risk_capital, 2)

            # Quét các nến tương lai để kiểm tra diễn biến lệnh
            outcome = None
            exit_price = None
            exit_time = None
            bars_held = 0
            current_sl = sl
            be_triggered = False
            partial_banked = False
            banked_pnl = 0.0

            max_future = min(i + 80, n_candles)
            future_idx = i + 1

            while future_idx < max_future:
                fc = candles[future_idx]
                fc_high = float(fc.high)
                fc_low = float(fc.low)
                bars_held = future_idx - i

                # Kiểm tra kích hoạt Break-Even tại 1.5R
                if request.enable_breakeven and not be_triggered:
                    if side == "BUY" and fc_high >= entry + (1.5 * sl_dist):
                        current_sl = entry
                        be_triggered = True
                    elif side == "SELL" and fc_low <= entry - (1.5 * sl_dist):
                        current_sl = entry
                        be_triggered = True

                # Kiểm tra chốt lời 50% TP1 tại 1.5R
                if request.enable_partial_tp and not partial_banked:
                    if (side == "BUY" and fc_high >= entry + (1.5 * sl_dist)) or (side == "SELL" and fc_low <= entry - (1.5 * sl_dist)):
                        partial_banked = True
                        banked_pnl = round(1.5 * sl_dist * (lots * 0.5) * 100.0, 2)
                        current_sl = entry

                # Kiểm tra khớp SL hoặc TP
                if side == "BUY":
                    if fc_low <= current_sl:
                        exit_price = current_sl
                        exit_time = fc.open_time
                        if be_triggered and not partial_banked:
                            outcome = "BREAKEVEN"
                            pnl = 0.0
                        elif partial_banked:
                            outcome = "WIN"
                            pnl = banked_pnl
                        else:
                            outcome = "LOSS"
                            pnl = -round(sl_dist * lots * 100.0, 2)
                        break
                    elif fc_high >= tp:
                        exit_price = tp
                        exit_time = fc.open_time
                        outcome = "WIN"
                        if partial_banked:
                            pnl = banked_pnl + round(tp_dist * (lots * 0.5) * 100.0, 2)
                        else:
                            pnl = round(tp_dist * lots * 100.0, 2)
                        break
                else:  # SELL
                    if fc_high >= current_sl:
                        exit_price = current_sl
                        exit_time = fc.open_time
                        if be_triggered and not partial_banked:
                            outcome = "BREAKEVEN"
                            pnl = 0.0
                        elif partial_banked:
                            outcome = "WIN"
                            pnl = banked_pnl
                        else:
                            outcome = "LOSS"
                            pnl = -round(sl_dist * lots * 100.0, 2)
                        break
                    elif fc_low <= tp:
                        exit_price = tp
                        exit_time = fc.open_time
                        outcome = "WIN"
                        if partial_banked:
                            pnl = banked_pnl + round(tp_dist * (lots * 0.5) * 100.0, 2)
                        else:
                            pnl = round(tp_dist * lots * 100.0, 2)
                        break

                future_idx += 1

            if outcome:
                balance += pnl
                if balance > peak_balance:
                    peak_balance = balance
                dd = peak_balance - balance
                if dd > max_drawdown_dollars:
                    max_drawdown_dollars = dd

                duration_secs = (exit_time - c.open_time).total_seconds() if exit_time else 0
                r_mult = "+0.0R"
                if outcome == "WIN":
                    r_mult = f"+{request.risk_reward_ratio:.1f}R"
                elif outcome == "LOSS":
                    r_mult = "-1.0R"
                elif outcome == "BREAKEVEN":
                    r_mult = "0.0R"

                trade_record = {
                    "trade_no": len(trades) + 1,
                    "side": side,
                    "entry_time": c.open_time.isoformat(),
                    "exit_time": exit_time.isoformat() if exit_time else None,
                    "bars_held": bars_held,
                    "duration_str": f"{bars_held} bars ({format_duration(duration_secs)})",
                    "lots": lots,
                    "expected_risk": expected_risk,
                    "entry_price": round(entry, 2),
                    "exit_price": round(exit_price, 2),
                    "stop_loss": round(sl, 2),
                    "take_profit": round(tp, 2),
                    "sl_distance": sl_dist,
                    "tp_distance": tp_dist,
                    "r_multiple": r_mult,
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
    loss_trades = sum(1 for t in trades if t["outcome"] == "LOSS")
    be_trades = sum(1 for t in trades if t["outcome"] == "BREAKEVEN")
    winrate = round((win_trades / (win_trades + loss_trades)) * 100, 2) if (win_trades + loss_trades) > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    net_pnl = round(balance - request.initial_balance, 2)
    max_dd_pct = round((max_drawdown_dollars / peak_balance) * 100, 2) if peak_balance > 0 else 0.0

    test_duration_secs = (candles[-1].open_time - candles[0].open_time).total_seconds()

    return {
        "summary": {
            "initial_balance": request.initial_balance,
            "final_balance": round(balance, 2),
            "net_pnl": net_pnl,
            "net_pnl_percent": round((net_pnl / request.initial_balance) * 100, 2),
            "total_trades": total_trades,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "be_trades": be_trades,
            "winrate_percent": winrate,
            "profit_factor": profit_factor,
            "max_drawdown_percent": max_dd_pct,
            "max_drawdown_dollars": round(max_drawdown_dollars, 2),
        },
        "test_specs": {
            "symbol": request.symbol,
            "timeframe": tf,
            "bars_requested": request.bars_count,
            "bars_tested": len(candles),
            "start_candle_time": candles[0].open_time.isoformat(),
            "end_candle_time": candles[-1].open_time.isoformat(),
            "duration_str": format_duration(test_duration_secs),
            "initial_balance": request.initial_balance,
            "risk_pct": request.risk_pct,
            "sizing_mode": request.sizing_mode,
            "atr_period": atr_period,
            "atr_sl_multiplier": request.atr_sl_multiplier,
            "risk_reward_ratio": request.risk_reward_ratio,
            "enable_breakeven": request.enable_breakeven,
            "enable_partial_tp": request.enable_partial_tp,
            "session_filter": request.session_filter,
        },
        "equity_curve": equity_curve,
        "trades": trades,
    }

