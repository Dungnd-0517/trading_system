from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import uuid


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


@dataclass
class PaperOrder:
    ticket: int
    symbol: str
    side: str
    lots: float
    entry: float
    stop_loss: float
    take_profit: float
    ticket_uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    slippage: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    close_reason: str | None = None
    status: OrderStatus = OrderStatus.FILLED
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_price: float | None = None
    realized_pnl: float | None = None
    close_time: datetime | None = None


class PaperEngine:
    def __init__(self, slippage_points: float = 1.0, point_size: float = 0.01, contract_size: float = 100.0):
        if slippage_points < 0 or point_size <= 0 or contract_size <= 0:
            raise ValueError("slippage must be non-negative and size values must be positive")
        self.slippage = slippage_points * point_size
        self.contract_size = contract_size
        self._next_ticket = 1
        self.orders: dict[int, PaperOrder] = {}

    def open_market(
        self, symbol: str, side: str, lots: float, bid: float, ask: float, stop_loss: float, take_profit: float
    ) -> PaperOrder:
        side = side.upper()
        if side not in {"BUY", "SELL"} or lots <= 0 or bid <= 0 or ask < bid:
            raise ValueError("invalid side, size, or quote")
        entry = ask + self.slippage if side == "BUY" else bid - self.slippage
        if side == "BUY" and not stop_loss < entry < take_profit:
            raise ValueError("BUY requires stop_loss < entry < take_profit")
        if side == "SELL" and not take_profit < entry < stop_loss:
            raise ValueError("SELL requires take_profit < entry < stop_loss")
        order = PaperOrder(
            ticket=self._next_ticket,
            symbol=symbol,
            side=side,
            lots=lots,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            slippage=self.slippage,
        )
        self.orders[order.ticket] = order
        self._next_ticket += 1
        return order

    def close_order(self, ticket: int, exit_price: float, reason: str = "MANUAL_CLOSE") -> PaperOrder | None:
        order = self.orders.get(ticket)
        if not order or order.status != OrderStatus.FILLED:
            return None
        direction = 1 if order.side == "BUY" else -1
        order.exit_price = exit_price
        order.realized_pnl = round((exit_price - order.entry) * direction * order.lots * self.contract_size, 2)
        order.close_reason = reason
        order.status = OrderStatus.CLOSED
        order.close_time = datetime.now(timezone.utc)
        return order

    def on_tick(self, symbol: str, bid: float, ask: float) -> list[PaperOrder]:
        closed = []
        for order in self.orders.values():
            if order.symbol != symbol or order.status != OrderStatus.FILLED:
                continue
            exit_price = bid if order.side == "BUY" else ask
            hit_stop = exit_price <= order.stop_loss if order.side == "BUY" else exit_price >= order.stop_loss
            hit_target = exit_price >= order.take_profit if order.side == "BUY" else exit_price <= order.take_profit
            if hit_stop or hit_target:
                order.exit_price = exit_price
                direction = 1 if order.side == "BUY" else -1
                order.realized_pnl = round((exit_price - order.entry) * direction * order.lots * self.contract_size, 2)
                order.close_reason = "SL_HIT" if hit_stop else "TP_HIT"
                order.status = OrderStatus.CLOSED
                order.close_time = datetime.now(timezone.utc)
                closed.append(order)
        return closed