from typing import Any

import httpx

from core.config import settings


class MT5Feed:
    def __init__(self, base_url: str = settings.mt5_bridge_url) -> None:
        self.base_url = base_url.rstrip("/")

    async def latest_tick(self, symbol: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.base_url}/ticks/{symbol}")
            response.raise_for_status()
            return response.json()