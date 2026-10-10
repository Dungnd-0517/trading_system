import asyncio
import concurrent.futures
from decimal import Decimal
import logging
import pytest
from sqlalchemy import delete

from core.database import engine, session_factory
from core.models import EpisodicTradeMemory, SimulatedOrder, SimulationAccount, StrategySignal, TradingKnowledge
from simulation.paper_worker import paper_worker

logger = logging.getLogger(__name__)


async def _clean_test_data_async():
    """Dọn dẹp sạch toàn bộ dữ liệu test trong DB và bộ nhớ, khôi phục tài khoản về $10,000.00"""
    # 0. Giải phóng các kết nối cũ từ loop trước (tránh asyncpg loop mismatch)
    try:
        await engine.dispose()
    except Exception:
        pass

    async with session_factory() as session:
        # 1. Xóa các ký ức trade test và tri thức test
        await session.execute(delete(EpisodicTradeMemory).where(EpisodicTradeMemory.is_test.is_(True)))
        await session.execute(delete(TradingKnowledge).where(TradingKnowledge.category == "TEST"))

        # 2. Xóa tất cả các lệnh test
        await session.execute(delete(SimulatedOrder).where(SimulatedOrder.is_test.is_(True)))

        # 3. Xóa tất cả các tín hiệu test
        await session.execute(delete(StrategySignal).where(StrategySignal.is_test.is_(True)))

        # 3. Khôi phục số dư tài khoản simulation_account về ban đầu $10,000.00 nếu có test lệnh
        acc = await session.get(SimulationAccount, 1)
        if acc:
            acc.current_balance = Decimal("10000.00")
            acc.equity = Decimal("10000.00")
            acc.margin_used = Decimal("0.00")

        await session.commit()

    # 4. Dọn dẹp in-memory test orders trong paper_worker
    test_tickets = [
        ticket for ticket, ord in list(paper_worker.engine.orders.items())
        if getattr(ord, "is_test", False)
    ]
    for ticket in test_tickets:
        paper_worker.engine.orders.pop(ticket, None)

    # 5. Giải phóng DB pool sau khi dọn dẹp
    try:
        await engine.dispose()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def auto_clean_test_data():
    """
    Autouse fixture cho TẤT CẢ các test:
    Sau mỗi lần chạy test bất kỳ, tự động dọn dẹp sạch dữ liệu test trong backend
    để không lưu lại rác trong database và không làm sai lệch số dư thực tế.
    """
    yield

    def _run_cleanup():
        asyncio.run(_clean_test_data_async())

    try:
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                fut = executor.submit(_run_cleanup)
                fut.result(timeout=10)
        else:
            _run_cleanup()
    except Exception as exc:
        print(f"Auto clean test data failed: {exc}")
        logger.error("Auto clean test data failed: %s", exc)
