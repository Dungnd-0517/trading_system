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
    initial_stop_loss: float = 0.0
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
    is_breakeven_moved: bool = False
    is_partial_closed: bool = False
    parent_ticket_id: int | None = None
    trailing_stop_price: float | None = None
    is_test: bool = False


class PaperEngine:
    def __init__(self, slippage_points: float = 1.0, point_size: float = 0.01, contract_size: float = 100.0):
        if slippage_points < 0 or point_size <= 0 or contract_size <= 0:
            raise ValueError("slippage must be non-negative and size values must be positive")
        self.slippage = slippage_points * point_size
        self.contract_size = contract_size
        self._next_ticket = 1
        self.orders: dict[int, PaperOrder] = {}

    def open_market(
        self,
        symbol: str,
        side: str,
        lots: float,
        bid: float,
        ask: float,
        stop_loss: float,
        take_profit: float,
        is_test: bool = False,
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
            initial_stop_loss=stop_loss,
            slippage=self.slippage,
            is_test=is_test,
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

    def check_and_apply_breakeven(self, order: PaperOrder, bid: float, ask: float, r_multiple: float = 1.5) -> bool:
        """Tự động dời Stop Loss về giá hòa vốn khi giá chạy đạt r_multiple R"""
        if order.is_breakeven_moved or order.status != OrderStatus.FILLED:
            return False

        init_sl = order.initial_stop_loss or order.stop_loss
        risk_dist = abs(order.entry - init_sl)
        if risk_dist <= 0:
            return False

        if order.side == "BUY" and bid >= order.entry + r_multiple * risk_dist:
            order.stop_loss = round(order.entry + 0.10, 2)
            order.is_breakeven_moved = True
            return True
        elif order.side == "SELL" and ask <= order.entry - r_multiple * risk_dist:
            order.stop_loss = round(order.entry - 0.10, 2)
            order.is_breakeven_moved = True
            return True

        return False

    def partial_close_order(
        self, ticket: int, exit_price: float, ratio: float = 0.5, reason: str = "PARTIAL_TP1"
    ) -> PaperOrder | None:
        """Chốt lời từng phần (mặc định 50%) và dời SL của phần còn lại về hòa vốn"""
        order = self.orders.get(ticket)
        if not order or order.status != OrderStatus.FILLED or order.lots <= 0.01:
            return None

        closed_lots = round(order.lots * ratio, 2)
        remaining_lots = round(order.lots - closed_lots, 2)
        if closed_lots <= 0 or remaining_lots <= 0:
            return None

        direction = 1 if order.side == "BUY" else -1
        pnl = round((exit_price - order.entry) * direction * closed_lots * self.contract_size, 2)

        # Tạo bản ghi phụ đại diện cho phần lot đã chốt
        partial_record = PaperOrder(
            ticket=self._next_ticket,
            symbol=order.symbol,
            side=order.side,
            lots=closed_lots,
            entry=order.entry,
            stop_loss=order.stop_loss,
            take_profit=exit_price,
            initial_stop_loss=order.initial_stop_loss,
            parent_ticket_id=order.ticket,
            status=OrderStatus.CLOSED,
            exit_price=exit_price,
            realized_pnl=pnl,
            close_reason=reason,
            close_time=datetime.now(timezone.utc),
            is_test=order.is_test,
        )
        self.orders[partial_record.ticket] = partial_record
        self._next_ticket += 1

        # Cập nhật lại vị thế gốc
        order.lots = remaining_lots
        order.is_partial_closed = True
        # Dời SL về Breakeven
        order.stop_loss = round(order.entry + (0.10 if order.side == "BUY" else -0.10), 2)
        order.is_breakeven_moved = True

        return partial_record

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