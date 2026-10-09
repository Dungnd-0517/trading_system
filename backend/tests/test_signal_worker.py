from datetime import datetime, timezone
from decimal import Decimal
import pandas as pd
import pytest
from sqlalchemy import delete

from ai_engine.signal_worker import SignalEngineWorker
from core.database import engine, session_factory
from core.models import MarketCandle, StrategySignal


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_signal_worker_insufficient_bars():
    worker = SignalEngineWorker()
    async with session_factory() as session:
        # Nếu DB chưa có đủ nến M15/H1/H4/D1 cho một symbol lạ ví dụ "UNKNOWN_SYM"
        sig = await worker.evaluate_signal("UNKNOWN_SYM", session)
        assert sig is None


@pytest.mark.anyio
async def test_signal_worker_mock_signal_generation(monkeypatch):
    worker = SignalEngineWorker()
    from ai_engine.strategy import Signal

    # Mock fetch_frames trả về đủ số nến
    dummy_df = pd.DataFrame(
        [{"open": 2680.0, "high": 2690.0, "low": 2675.0, "close": 2685.0}],
        index=[pd.Timestamp("2026-10-08 14:00:00", tz="UTC")],
    )

    async def mock_fetch(session, symbol):
        return {
            "D1": pd.concat([dummy_df] * 35),
            "H4": pd.concat([dummy_df] * 45),
            "H1": pd.concat([dummy_df] * 65),
            "M15": pd.concat([dummy_df] * 65),
        }

    monkeypatch.setattr(worker, "fetch_frames", mock_fetch)

    # Mock generate_signal trả về 1 Signal hợp lệ
    mock_sig = Signal(
        time=pd.Timestamp("2026-10-08 14:15:00", tz="UTC"),
        side="long",
        entry=2685.0,
        sl=2680.0,
        tp=2695.0,
        rr=2.0,
        reason="long | D1/H4 bias | H1 OB | M15 CHoCH | London KZ",
    )
    monkeypatch.setattr("ai_engine.strategy.generate_signal", lambda frames, cfg: mock_sig)

    async def mock_publish(channel, message):
        return 1

    monkeypatch.setattr("core.redis_client.client.publish", mock_publish)

    async with session_factory() as session:
        await session.execute(
            delete(StrategySignal).where(
                StrategySignal.symbol == "TEST_XAU",
                StrategySignal.generated_at == mock_sig.time.to_pydatetime(),
            )
        )
        await session.commit()

        record = await worker.evaluate_signal("TEST_XAU", session)
        assert record is not None
        assert record.symbol == "TEST_XAU"
        assert record.side == "BUY"
        assert record.entry_price == Decimal("2685.00")
        assert record.stop_loss == Decimal("2680.00")
        assert record.take_profit_1 == Decimal("2695.00")
        assert record.risk_reward == Decimal("2.00")
        assert record.status in ("PENDING", "INVALIDATED")

        # Cleanup
        await session.execute(
            delete(StrategySignal).where(StrategySignal.symbol == "TEST_XAU")
        )
        await session.commit()
