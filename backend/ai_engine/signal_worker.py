import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine import sessions, strategy
from ai_engine.news_guard import news_circuit_breaker
from core.database import session_factory
from core.models import MarketCandle, StrategySignal, SystemTradingConfig
from core.redis_client import client as redis_client

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "swing_left": 3,
    "swing_right": 3,
    "m15_swing": 2,
    "require_d1_alignment": True,
    "require_choch": True,
    "fvg_min_atr": 0.3,
    "poi_max_age_h1": 48,
    "tap_lookback_m15": 5,
    "sl_buffer_atr": 0.5,
    "max_risk_atr15": 3.0,
    "min_rr": 2.0,
    "default_rr": 3.0,
    "kill_zones": ("london", "ny_am", "ny_pm"),
}


class SignalEngineWorker:
    """Worker chạy nền tự động phát hiện và sinh tín hiệu giao dịch SMC theo chu kỳ nến M15"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.last_evaluated_m15_time: int | None = None
        self._running = False

    async def fetch_frames(self, session: AsyncSession, symbol: str = "XAUUSD") -> dict[str, pd.DataFrame]:
        limits = {"D1": 40, "H4": 50, "H1": 80, "M15": 80}
        frames: dict[str, pd.DataFrame] = {}

        for tf, limit in limits.items():
            query = (
                select(MarketCandle)
                .where(MarketCandle.symbol == symbol, MarketCandle.timeframe == tf)
                .order_by(MarketCandle.open_time.desc())
                .limit(limit)
            )
            rows = (await session.scalars(query)).all()
            if not rows:
                frames[tf] = pd.DataFrame(columns=["open", "high", "low", "close"])
                continue

            data = [
                {
                    "time": row.open_time if row.open_time.tzinfo else row.open_time.replace(tzinfo=timezone.utc),
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                }
                for row in reversed(rows)
            ]
            df = pd.DataFrame(data).set_index("time")
            frames[tf] = df

        return frames

    def get_session_name(self, ts: datetime) -> str:
        t_ny = sessions.ny_time(ts)
        h = t_ny.hour + t_ny.minute / 60.0
        if 2.0 <= h < 5.0:
            return "London Kill Zone"
        if 7.0 <= h < 10.0:
            return "New York AM Kill Zone"
        if 13.5 <= h < 16.0:
            return "New York PM Kill Zone"
        if 20.0 <= h < 24.0 or h < 2.0:
            return "Asia Session"
        return "Off-Session Window"

    async def evaluate_signal(
        self, symbol: str = "XAUUSD", session: AsyncSession | None = None, is_test: bool = False
    ) -> StrategySignal | None:
        """Đánh giá tín hiệu SMC từ dữ liệu nến thực tế trong DB"""
        own_session = session is None
        sess = session or session_factory()

        try:
            frames = await self.fetch_frames(sess, symbol)
            # Kiểm tra số lượng nến tối thiểu
            for tf, min_bars in strategy.MIN_BARS.items():
                if len(frames.get(tf, [])) < min_bars:
                    logger.debug("Chưa đủ nến cho timeframe %s (cần %d, có %d)", tf, min_bars, len(frames.get(tf, [])))
                    return None

            sig = strategy.generate_signal(frames, self.config)
            if sig is None:
                return None

            side_upper = "BUY" if sig.side.lower() == "long" else "SELL"
            gen_time = sig.time.to_pydatetime()
            if gen_time.tzinfo is None:
                gen_time = gen_time.replace(tzinfo=timezone.utc)

            # Kiểm tra xem tín hiệu này đã được ghi nhận trước đó chưa (tránh duplicate)
            existing = await sess.scalar(
                select(StrategySignal).where(
                    StrategySignal.symbol == symbol,
                    StrategySignal.generated_at == gen_time,
                    StrategySignal.side == side_upper,
                )
            )
            if existing:
                return existing

            session_name = self.get_session_name(gen_time)
            entry_dec = Decimal(f"{sig.entry:.2f}")
            sl_dec = Decimal(f"{sig.sl:.2f}")
            tp1_dec = Decimal(f"{sig.tp:.2f}")
            rr_dec = Decimal(f"{sig.rr:.2f}")

            # Tính TP2 (mở rộng thêm 1R)
            risk = abs(sig.entry - sig.sl)
            tp2_val = sig.entry + 3.5 * risk if side_upper == "BUY" else sig.entry - 3.5 * risk
            tp2_dec = Decimal(f"{tp2_val:.2f}")

            # Kiểm tra Macro News Circuit Breaker
            is_active, cb_reason, _ = await news_circuit_breaker.is_circuit_active(sess, gen_time)
            status = "INVALIDATED" if is_active else "PENDING"
            inv_reason = f"Circuit Breaker kích hoạt: {cb_reason}" if is_active else None

            signal_record = StrategySignal(
                symbol=symbol,
                side=side_upper,
                generated_at=gen_time,
                session_name=session_name,
                entry_price=entry_dec,
                stop_loss=sl_dec,
                take_profit_1=tp1_dec,
                take_profit_2=tp2_dec,
                risk_reward=rr_dec,
                status=status,
                invalidated_reason=inv_reason,
                reason=sig.reason,
                is_test=is_test,
            )
            sess.add(signal_record)
            await sess.commit()
            await sess.refresh(signal_record)

            # Phát sự kiện qua Redis nếu tín hiệu hợp lệ
            if status == "PENDING":
                payload = {
                    "type": "signal.new",
                    "data": {
                        "id": signal_record.id,
                        "symbol": signal_record.symbol,
                        "side": signal_record.side,
                        "entry_price": float(signal_record.entry_price),
                        "stop_loss": float(signal_record.stop_loss),
                        "take_profit_1": float(signal_record.take_profit_1),
                        "take_profit_2": float(signal_record.take_profit_2) if signal_record.take_profit_2 else None,
                        "risk_reward": float(signal_record.risk_reward),
                        "status": signal_record.status,
                        "reason": signal_record.reason,
                        "session_name": signal_record.session_name,
                        "timestamp": int(signal_record.generated_at.timestamp()),
                    },
                }
                try:
                    await redis_client.publish("market:signals", json.dumps(payload))
                    logger.info("New SMC signal generated: ID #%d, %s %s at %s", signal_record.id, symbol, side_upper, entry_dec)
                except Exception as exc:
                    logger.debug("Failed to publish signal to Redis: %s", exc)

                try:
                    from simulation.auto_executor import auto_executor
                    asyncio.create_task(auto_executor.on_new_signal(signal_record))
                except Exception as exc:
                    logger.debug("Failed to auto execute signal: %s", exc)

            return signal_record

        finally:
            if own_session:
                await sess.close()

    async def run(self) -> None:
        """Loop lắng nghe tick và định kỳ đánh giá tín hiệu khi nến M15 mới hoàn thành"""
        self._running = True
        logger.info("SignalEngineWorker started")

        while self._running:
            try:
                # Kiểm tra nến M15 gần nhất mỗi 15 giây
                async with session_factory() as session:
                    latest_m15 = await session.scalar(
                        select(MarketCandle)
                        .where(MarketCandle.symbol == "XAUUSD", MarketCandle.timeframe == "M15")
                        .order_by(MarketCandle.open_time.desc())
                        .limit(1)
                    )
                    if latest_m15:
                        m15_ts = int(latest_m15.open_time.timestamp())
                        if self.last_evaluated_m15_time is None or m15_ts > self.last_evaluated_m15_time:
                            self.last_evaluated_m15_time = m15_ts
                            await self.evaluate_signal("XAUUSD", session)

                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Error in SignalEngineWorker loop: %s", exc)
                await asyncio.sleep(15)

    def stop(self) -> None:
        self._running = False


signal_worker = SignalEngineWorker()
