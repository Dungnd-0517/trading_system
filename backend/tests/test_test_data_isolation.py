from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select

from core.database import session_factory
from core.models import SimulatedOrder, SimulationAccount, StrategySignal
from main import app
from simulation.paper_worker import paper_worker


@pytest.mark.anyio
async def test_test_orders_isolation_and_api_filtering():
    # 1. Tạo 1 test order qua paper_worker với is_test=True
    test_order = await paper_worker.open_order(
        symbol="XAUUSD",
        side="BUY",
        lots=0.1,
        stop_loss=2680.0,
        take_profit=2700.0,
        quote=(2685.0, 2685.2),
        is_test=True,
    )
    assert test_order["is_test"] is True

    # 2. Gọi API GET /api/v1/orders (mặc định include_test=False) -> Không chứa test order
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/orders")
        assert res.status_code == 200
        orders = res.json()
        assert all(o["is_test"] is False for o in orders)
        assert not any(o["id"] == test_order["id"] for o in orders)

        # 3. Gọi API GET /api/v1/orders?include_test=true -> Có chứa test order
        res_with_test = await client.get("/api/v1/orders?include_test=true")
        assert res_with_test.status_code == 200
        orders_with_test = res_with_test.json()
        assert any(o["id"] == test_order["id"] for o in orders_with_test)

        # 4. Kiểm tra open_positions_count trên /account không tính lệnh test
        res_acc = await client.get("/api/v1/orders/account")
        assert res_acc.status_code == 200
        assert res_acc.json()["open_positions_count"] == 0
