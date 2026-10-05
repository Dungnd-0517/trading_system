import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any
import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from core.database import session_factory
from core.interfaces.executor import BaseOrderExecutor
from core.models import SimulatedOrder, SimulationAccount
from core.redis_client import client as redis_client
from simulation.paper_engine import OrderStatus, PaperEngine, PaperOrder

logger = logging.getLogger(__name__)


class PaperEngineWorker(BaseOrderExecutor):
    def __init__(self, engine: PaperEngine | None = None) -> None:
        self.engine = engine or PaperEngine()
        self.latest_quotes: dict[str, dict[str, float]] = {
            "XAUUSD": {"bid": 2685.0, "ask": 2685.2},
            "BTCUSDT": {"bid": 65000.0, "ask": 65000.0},
        }
        self._running = False

    async def initialize(self) -> None:
        """Nạp các lệnh đang mở từ PostgreSQL vào bộ nhớ của PaperEngine"""
        async with session_factory() as session:
            # Khởi tạo simulation_account nếu chưa có
            account = await session.scalar(select(SimulationAccount).where(SimulationAccount.id == 1))
            if not account:
                session.add(
                    SimulationAccount(
                        id=1,
                        initial_balance=Decimal("10000.00"),
                        current_balance=Decimal("10000.00"),
                        equity=Decimal("10000.00"),
                        margin_used=Decimal("0.00"),
                    )
                )
                await session.commit()

            rows = (
                await session.scalars(
                    select(SimulatedOrder).where(SimulatedOrder.status.in_(["OPEN", "FILLED"]))
                )
            ).all()

            for row in rows:
                order = PaperOrder(
                    ticket=row.id,
                    ticket_uuid=row.ticket_uuid if row.ticket_uuid else uuid.uuid4(),
                    symbol=row.symbol,
                    side=row.order_type,
                    lots=float(row.lot_size),
                    entry=float(row.entry_price),
                    stop_loss=float(row.stop_loss),
                    take_profit=float(row.take_profit),
                    slippage=float(row.slippage or 0.0),
                    commission=float(row.commission or 0.0),
                    swap=float(row.swap or 0.0),
                    status=OrderStatus.FILLED,
                    open_time=row.open_time,
                )
                self.engine.orders[order.ticket] = order
                self.engine._next_ticket = max(self.engine._next_ticket, row.id + 1)

            logger.info("PaperEngine initialized with %d active orders", len(rows))

    async def run(self) -> None:
        """Background worker lắng nghe Redis channel market:ticks để quét SL/TP"""
        await self.initialize()
        self._running = True
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("market:ticks")
        logger.info("PaperEngineWorker subscribed to market:ticks")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    if payload.get("type") == "chart.update":
                        symbol = payload.get("symbol", "").upper()
                        price_info = payload.get("price") or {}
                        close_price = payload.get("candle", {}).get("close") or price_info.get("value") or 0.0
                        bid = float(price_info.get("bid") or close_price)
                        ask = float(price_info.get("ask") or close_price)

                        if bid > 0 and ask > 0 and symbol:
                            self.latest_quotes[symbol] = {"bid": bid, "ask": ask}
                            await self.on_tick(symbol, bid, ask)
                except Exception as exc:
                    logger.debug("Error processing tick in PaperEngineWorker: %s", exc)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe("market:ticks")
            await pubsub.aclose()

    def stop(self) -> None:
        self._running = False

    async def on_tick(self, symbol: str, bid: float, ask: float) -> list[dict[str, Any]]:
        closed_orders = self.engine.on_tick(symbol, bid, ask)
        if not closed_orders:
            return []

        events = []
        for order in closed_orders:
            event_data = await self._persist_closed_order(order)
            events.append(event_data)
        return events

    async def open_order(
        self,
        symbol: str,
        side: str,
        lots: float,
        stop_loss: float,
        take_profit: float,
        strategy_trigger: str | None = None,
        quote: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        symbol = symbol.upper()
        if quote is not None:
            bid, ask = quote
        else:
            q = self.latest_quotes.get(symbol, {"bid": 2685.0, "ask": 2685.2})
            bid, ask = q["bid"], q["ask"]

        # 1. Khớp lệnh in-memory qua PaperEngine
        order = self.engine.open_market(
            symbol=symbol,
            side=side,
            lots=lots,
            bid=bid,
            ask=ask,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # 2. Persist vào PostgreSQL
        async with session_factory() as session:
            db_order = SimulatedOrder(
                ticket_uuid=order.ticket_uuid,
                symbol=order.symbol,
                order_type=order.side,
                status="FILLED",
                lot_size=Decimal(str(order.lots)),
                entry_price=Decimal(f"{order.entry:.4f}"),
                stop_loss=Decimal(f"{order.stop_loss:.4f}"),
                take_profit=Decimal(f"{order.take_profit:.4f}"),
                slippage=Decimal(f"{order.slippage:.4f}"),
                commission=Decimal(f"{order.commission:.2f}"),
                swap=Decimal(f"{order.swap:.2f}"),
                open_time=order.open_time,
                strategy_trigger=strategy_trigger,
            )
            session.add(db_order)
            await session.commit()
            await session.refresh(db_order)

            # Cập nhật lại ticket ID cho in-memory order khớp với DB id
            if order.ticket != db_order.id:
                self.engine.orders.pop(order.ticket, None)
                order.ticket = db_order.id
                self.engine.orders[order.ticket] = order

        # 3. Publish order.update event lên Redis channel paper:orders
        order_dict = self._order_to_dict(order)
        event = {
            "type": "order.update",
            "event": "ORDER_FILLED",
            "data": order_dict,
        }
        await self._broadcast_order_event(event)
        return order_dict

    async def close_order(self, order_id: int, reason: str = "MANUAL_CLOSE") -> dict[str, Any]:
        order = self.engine.orders.get(order_id)
        if not order or order.status != OrderStatus.FILLED:
            # Thử tìm trong DB nếu bộ nhớ chưa có
            async with session_factory() as session:
                db_order = await session.get(SimulatedOrder, order_id)
                if not db_order or db_order.status == "CLOSED":
                    raise ValueError(f"Order #{order_id} not found or already closed")
                q = self.latest_quotes.get(db_order.symbol, {"bid": float(db_order.entry_price), "ask": float(db_order.entry_price)})
                exit_price = q["bid"] if db_order.order_type == "BUY" else q["ask"]
                direction = 1 if db_order.order_type == "BUY" else -1
                realized_pnl = round(
                    (exit_price - float(db_order.entry_price)) * direction * float(db_order.lot_size) * self.engine.contract_size, 2
                )
                now = datetime.now(timezone.utc)
                db_order.exit_price = Decimal(f"{exit_price:.4f}")
                db_order.realized_pnl = Decimal(f"{realized_pnl:.2f}")
                db_order.close_reason = reason
                db_order.status = "CLOSED"
                db_order.close_time = now
                await session.commit()
                order_dict = {
                    "id": db_order.id,
                    "ticket_uuid": str(db_order.ticket_uuid),
                    "symbol": db_order.symbol,
                    "order_type": db_order.order_type,
                    "status": "CLOSED",
                    "lot_size": float(db_order.lot_size),
                    "entry_price": float(db_order.entry_price),
                    "exit_price": exit_price,
                    "stop_loss": float(db_order.stop_loss),
                    "take_profit": float(db_order.take_profit),
                    "open_time": db_order.open_time.isoformat(),
                    "close_time": now.isoformat(),
                    "realized_pnl": realized_pnl,
                    "close_reason": reason,
                }
                await self._broadcast_order_event({"type": "order.update", "event": "ORDER_CLOSED", "data": order_dict})
                return order_dict

        q = self.latest_quotes.get(order.symbol, {"bid": order.entry, "ask": order.entry})
        exit_price = q["bid"] if order.side == "BUY" else q["ask"]
        closed_order = self.engine.close_order(order_id, exit_price, reason=reason)
        assert closed_order is not None
        return await self._persist_closed_order(closed_order)

    async def _persist_closed_order(self, order: PaperOrder) -> dict[str, Any]:
        async with session_factory() as session:
            # 1. Cập nhật trạng thái lệnh trong DB
            await session.execute(
                update(SimulatedOrder)
                .where(SimulatedOrder.id == order.ticket)
                .values(
                    status="CLOSED",
                    exit_price=Decimal(f"{order.exit_price:.4f}"),
                    realized_pnl=Decimal(f"{order.realized_pnl:.2f}"),
                    close_reason=order.close_reason,
                    close_time=order.close_time,
                )
            )

            # 2. Cập nhật số dư tài khoản simulation_account
            account = await session.scalar(select(SimulationAccount).where(SimulationAccount.id == 1))
            if account and order.realized_pnl is not None:
                pnl_dec = Decimal(str(order.realized_pnl))
                account.current_balance += pnl_dec
                account.equity += pnl_dec
                account.updated_at = datetime.now(timezone.utc)

            await session.commit()

        # 3. Broadcast qua Redis
        order_dict = self._order_to_dict(order)
        event = {
            "type": "order.update",
            "event": "ORDER_CLOSED",
            "data": order_dict,
        }
        await self._broadcast_order_event(event)
        return order_dict

    async def _broadcast_order_event(self, event: dict[str, Any]) -> None:
        try:
            await redis_client.publish("paper:orders", json.dumps(event, separators=(",", ":")))
        except Exception as exc:
            logger.warning("Failed to publish order event to Redis: %s", exc)

    @staticmethod
    def _order_to_dict(order: PaperOrder) -> dict[str, Any]:
        return {
            "id": order.ticket,
            "ticket_uuid": str(order.ticket_uuid),
            "symbol": order.symbol,
            "order_type": order.side,
            "status": str(order.status),
            "lot_size": order.lots,
            "entry_price": order.entry,
            "exit_price": order.exit_price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "open_time": order.open_time.isoformat() if order.open_time else None,
            "close_time": order.close_time.isoformat() if order.close_time else None,
            "realized_pnl": order.realized_pnl,
            "close_reason": order.close_reason,
        }


# Singleton worker instance
paper_worker = PaperEngineWorker()
