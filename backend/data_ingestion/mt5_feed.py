from datetime import datetime, timezone
from typing import Any

import httpx

from core.config import settings


class MT5Feed:
    """Client giao tiếp với MT5-bridge FastAPI service.

    Cung cấp:
    - latest_tick / ticks_since: lấy tick real-time (dùng cho CandleAggregator)
    - get_candles: lấy lịch sử nến OHLCV từ MT5 theo khoảng thời gian
    - get_latest_candles: lấy N nến gần nhất (dùng khi load chart)
    - health: kiểm tra trạng thái kết nối MT5
    - reconnect: yêu cầu bridge thử kết nối lại
    """

    def __init__(self, base_url: str = settings.mt5_bridge_url) -> None:
        self.base_url = base_url.rstrip("/")

    async def health(self) -> dict[str, Any]:
        """Kiểm tra trạng thái kết nối MT5 bridge."""
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def reconnect(self) -> dict[str, Any]:
        """Yêu cầu bridge thử kết nối lại MT5."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.base_url}/reconnect")
            response.raise_for_status()
            return response.json()

    async def latest_tick(self, symbol: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base_url}/ticks/{symbol}")
            response.raise_for_status()
            return response.json()

    async def ticks_since(self, symbol: str, since_ms: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.base_url}/ticks/{symbol}/since",
                params={"since_ms": since_ms},
            )
            response.raise_for_status()
            payload = response.json()
        ticks = payload.get("ticks")
        if not isinstance(ticks, list):
            raise ValueError("MT5 bridge returned an invalid tick batch")
        return ticks

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "M1",
        from_date: str = "2026-01-01",
        count: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Lấy lịch sử nến từ MT5 bắt đầu từ from_date.
        Trả về danh sách candle dict với keys: time, open, high, low, close, volume.

        Args:
            symbol: Ký hiệu giao dịch (ví dụ: XAUUSD)
            timeframe: Khung thời gian (M1, M5, M15, H1, H4, D1)
            from_date: Ngày bắt đầu định dạng YYYY-MM-DD (UTC)
            count: Số nến tối đa mỗi lần gọi (tối đa 99000)
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/candles/{symbol}",
                params={"timeframe": timeframe, "from_date": from_date, "count": count},
            )
            response.raise_for_status()
            payload = response.json()
        candles = payload.get("candles")
        if not isinstance(candles, list):
            raise ValueError(f"MT5 bridge returned invalid candles for {symbol} {timeframe}")
        return candles

    async def get_latest_candles(
        self,
        symbol: str,
        timeframe: str = "M1",
        count: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Lấy N nến gần nhất từ MT5 (dùng để hiển thị biểu đồ 500 nến gần nhất).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/candles/{symbol}/latest",
                params={"timeframe": timeframe, "count": count},
            )
            response.raise_for_status()
            payload = response.json()
        candles = payload.get("candles")
        if not isinstance(candles, list):
            raise ValueError(f"MT5 bridge returned invalid latest candles for {symbol} {timeframe}")
        return candles

    async def is_connected(self) -> bool:
        """Trả về True nếu MT5 bridge đang kết nối thành công."""
        try:
            h = await self.health()
            return bool(h.get("mt5_connected", False))
        except Exception:
            return False