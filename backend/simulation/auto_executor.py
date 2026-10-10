from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_factory
from core.models import SimulatedOrder, SimulationAccount, StrategySignal, SystemTradingConfig
from simulation.paper_worker import paper_worker

logger = logging.getLogger(__name__)


class AutoExecutionController:
    """Bộ điều phối thực thi lệnh tự động hoặc theo yêu cầu trader từ tín hiệu SMC"""

    @staticmethod
    def calculate_lot_size(equity: float, risk_pct: float, entry: float, sl: float) -> float:
        risk_dist = abs(entry - sl)
        if risk_dist <= 0:
            return 0.10
        risk_amount = equity * (risk_pct / 100.0)
        lots = risk_amount / (risk_dist * 100.0)
        return max(0.01, min(5.00, round(lots, 2)))

    async def execute_signal(
        self,
        signal_id: int,
        session: AsyncSession | None = None,
        force_manual: bool = False,
        is_test: bool = False,
    ) -> dict[str, Any]:
        own_session = session is None
        sess = session or session_factory()

        try:
            signal = await sess.get(StrategySignal, signal_id)
            if not signal:
                raise ValueError(f"Signal #{signal_id} not found")

            if signal.status == "EXECUTED":
                raise ValueError(f"Signal #{signal_id} already executed")

            if signal.status == "INVALIDATED" and not force_manual:
                raise ValueError(f"Signal #{signal_id} is INVALIDATED ({signal.invalidated_reason})")

            # Đọc cấu hình hệ thống
            cfg = await sess.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
            mode = cfg.execution_mode if cfg else "MANUAL"
            risk_pct = float(cfg.risk_per_trade_percent) if cfg else 1.0
            max_open = cfg.max_open_positions if cfg else 2

            if not force_manual and mode != "FULL_AUTO":
                raise ValueError(f"Auto-trading is not enabled (current mode: {mode})")

            # Kiểm tra số lượng vị thế đang mở
            open_count = await sess.scalar(
                select(func.count()).select_from(SimulatedOrder).where(SimulatedOrder.status.in_(["OPEN", "FILLED"]))
            ) or 0
            if open_count >= max_open:
                raise ValueError(f"Max open positions reached ({open_count}/{max_open})")

            # Lấy equity tài khoản để tính khối lượng lot
            acc = await sess.scalar(select(SimulationAccount).where(SimulationAccount.id == 1))
            equity = float(acc.equity) if acc else 10000.0

            entry_p = float(signal.entry_price)
            sl_p = float(signal.stop_loss)
            tp_p = float(signal.take_profit_1)
            lots = self.calculate_lot_size(equity, risk_pct, entry_p, sl_p)

            # Mở vị thế qua Paper Worker (gắn cờ is_test nếu signal là test)
            is_test_flag = is_test or bool(getattr(signal, "is_test", False))
            order_res = await paper_worker.open_order(
                symbol=signal.symbol,
                side=signal.side,
                lots=lots,
                stop_loss=sl_p,
                take_profit=tp_p,
                strategy_trigger=f"SMC #{signal.id}: {signal.reason}",
                is_test=is_test_flag,
            )

            # Cập nhật trạng thái tín hiệu
            signal.status = "EXECUTED"
            signal.executed_order_id = order_res["id"]
            await sess.commit()

            logger.info("Signal #%d successfully executed into Order #%d (Lots: %.2f)", signal.id, order_res["id"], lots)
            return {
                "signal_id": signal.id,
                "order": order_res,
                "status": "EXECUTED",
            }
        finally:
            if own_session:
                await sess.close()

    async def on_new_signal(self, signal: StrategySignal) -> None:
        """Callback khi SignalEngineWorker sinh ra tín hiệu mới: tự động mở lệnh nếu FULL_AUTO"""
        async with session_factory() as session:
            cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
            if cfg and cfg.execution_mode == "FULL_AUTO" and signal.status == "PENDING":
                try:
                    await self.execute_signal(signal.id, session=session, force_manual=False)
                except Exception as exc:
                    logger.warning("Auto execution failed for signal #%d: %s", signal.id, exc)


auto_executor = AutoExecutionController()
