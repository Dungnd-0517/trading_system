from datetime import datetime, timedelta, timezone
from typing import Any
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import EconomicEvent, SystemTradingConfig
from core.redis_client import client as redis_client

logger = logging.getLogger(__name__)


class NewsCircuitBreaker:
    """Bộ ngắt mạch tự động tạm dừng giao dịch khi có sự kiện kinh tế 3 sao sắp diễn ra"""

    def __init__(self, default_buffer_mins: int = 30) -> None:
        self.default_buffer_mins = default_buffer_mins
        self._last_active_state: bool | None = None

    async def is_circuit_active(
        self,
        session: AsyncSession,
        target_time: datetime | None = None,
        buffer_mins: int | None = None,
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        now = target_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Lấy cấu hình từ DB nếu có
        cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
        if cfg and not cfg.news_circuit_breaker_enabled:
            return False, None, None

        mins = buffer_mins if buffer_mins is not None else (cfg.news_circuit_breaker_buffer_mins if cfg else self.default_buffer_mins)
        start_win = now - timedelta(minutes=mins)
        end_win = now + timedelta(minutes=mins)

        query = (
            select(EconomicEvent)
            .where(
                EconomicEvent.impact_stars == 3,
                EconomicEvent.currency == "USD",
                EconomicEvent.event_timestamp.is_not(None),
                EconomicEvent.event_timestamp >= start_win,
                EconomicEvent.event_timestamp <= end_win,
            )
            .order_by(EconomicEvent.event_timestamp.asc())
            .limit(1)
        )
        event = await session.scalar(query)
        if not event or not event.event_timestamp:
            return False, None, None

        diff_seconds = int((event.event_timestamp - now).total_seconds())
        diff_mins = round(diff_seconds / 60.0, 1)

        info = {
            "id": event.id,
            "title": event.title,
            "currency": event.currency,
            "impact_stars": event.impact_stars,
            "event_timestamp": event.event_timestamp.isoformat(),
            "time_diff_minutes": diff_mins,
        }

        if diff_seconds > 0:
            reason = f"Tin đỏ 3 sao '{event.title}' sẽ phát hành trong {abs(diff_mins):.0f} phút nữa"
        else:
            reason = f"Tin đỏ 3 sao '{event.title}' vừa phát hành cách đây {abs(diff_mins):.0f} phút"

        return True, reason, info

    async def broadcast_status(self, session: AsyncSession) -> None:
        """Kiểm tra và broadcast event ra Redis nếu trạng thái thay đổi"""
        active, reason, info = await self.is_circuit_active(session)
        if active != self._last_active_state:
            self._last_active_state = active
            payload = {
                "type": "circuit_breaker.update",
                "active": active,
                "reason": reason,
                "event": info,
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
            }
            try:
                await redis_client.publish("market:circuit_breaker", json.dumps(payload))
            except Exception as exc:
                logger.debug("Failed to publish circuit breaker update: %s", exc)


news_circuit_breaker = NewsCircuitBreaker()
