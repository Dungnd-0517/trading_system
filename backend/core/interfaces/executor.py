from abc import ABC, abstractmethod
from typing import Any


class BaseOrderExecutor(ABC):
    @abstractmethod
    async def open_order(
        self,
        symbol: str,
        side: str,
        lots: float,
        stop_loss: float,
        take_profit: float,
        strategy_trigger: str | None = None,
    ) -> dict[str, Any]:
        """Tạo và khớp một vị thế mới với giá thị trường kèm slippage"""
        pass

    @abstractmethod
    async def close_order(self, order_id: int, reason: str = "MANUAL_CLOSE") -> dict[str, Any]:
        """Đóng vị thế theo yêu cầu thủ công hoặc khẩn cấp"""
        pass

    @abstractmethod
    async def on_tick(self, symbol: str, bid: float, ask: float) -> list[dict[str, Any]]:
        """Quét và xử lý tự động SL/TP theo từng tick thị trường"""
        pass
