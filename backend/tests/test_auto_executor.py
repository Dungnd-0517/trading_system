from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import delete

from core.database import engine, session_factory
from core.models import StrategySignal, SystemTradingConfig
from simulation.auto_executor import AutoExecutionController


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_calculate_lot_size():
    ctrl = AutoExecutionController()
    # Equity $10,000, 1% risk = $100. Entry 2685, SL 2680 (Risk distance $5 = 500 points) -> Lots = 100 / (5 * 100) = 0.20 lots
    lots = ctrl.calculate_lot_size(equity=10000.0, risk_pct=1.0, entry=2685.0, sl=2680.0)
    assert lots == 0.20

    # Test clamping minimum 0.01
    tiny_lots = ctrl.calculate_lot_size(equity=100.0, risk_pct=0.1, entry=2685.0, sl=2680.0)
    assert tiny_lots == 0.01

    # Test clamping maximum 5.0
    large_lots = ctrl.calculate_lot_size(equity=1000000.0, risk_pct=5.0, entry=2685.0, sl=2684.0)
    assert large_lots == 5.0


@pytest.mark.anyio
async def test_execute_signal_manual_mode_requires_force():
    ctrl = AutoExecutionController()
    async with session_factory() as session:
        # Đảm bảo config là MANUAL và max_open đủ lớn cho test
        cfg = await session.get(SystemTradingConfig, 1)
        if cfg:
            cfg.execution_mode = "MANUAL"
            cfg.max_open_positions = 10
            await session.commit()

        # Tạo signal test
        now = datetime.now(timezone.utc)
        sig = StrategySignal(
            symbol="XAUUSD",
            side="BUY",
            generated_at=now,
            session_name="London Kill Zone",
            entry_price=Decimal("2685.0000"),
            stop_loss=Decimal("2680.0000"),
            take_profit_1=Decimal("2695.0000"),
            risk_reward=Decimal("2.00"),
            status="PENDING",
            reason="Test Signal",
        )
        session.add(sig)
        await session.commit()
        await session.refresh(sig)

        # 1. Thử execute không có force_manual ở chế độ MANUAL -> ném ValueError
        with pytest.raises(ValueError, match="Auto-trading is not enabled"):
            await ctrl.execute_signal(sig.id, session=session, force_manual=False)

        # 2. Execute với force_manual=True -> Thành công
        res = await ctrl.execute_signal(sig.id, session=session, force_manual=True)
        assert res["status"] == "EXECUTED"
        assert res["order"]["symbol"] == "XAUUSD"

        # Cleanup
        await session.execute(delete(StrategySignal).where(StrategySignal.id == sig.id))
        await session.commit()
