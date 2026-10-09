from datetime import datetime, timezone
from decimal import Decimal
import httpx
import pytest

from core.database import engine, session_factory
from core.models import MarketCandle, SimulatedOrder, StrategySignal, SystemTradingConfig
from main import app


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_get_and_update_trading_config():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Get config
        res = await client.get("/api/v1/strategy/config")
        assert res.status_code == 200
        data = res.json()
        assert "execution_mode" in data
        assert "risk_per_trade_percent" in data

        # 2. Update config
        update_payload = {
            "execution_mode": "FULL_AUTO",
            "risk_per_trade_percent": 1.5,
            "breakeven_r_multiple": 2.0,
            "enable_partial_tp": True,
            "news_circuit_breaker_enabled": True,
        }
        res_put = await client.put("/api/v1/strategy/config", json=update_payload)
        assert res_put.status_code == 200
        res_data = res_put.json()
        assert res_data["config"]["execution_mode"] == "FULL_AUTO"
        assert res_data["config"]["risk_per_trade_percent"] == 1.5

        # Revert back to MANUAL
        await client.put("/api/v1/strategy/config", json={"execution_mode": "MANUAL", "risk_per_trade_percent": 1.0})


@pytest.mark.anyio
async def test_list_and_evaluate_signals():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # List signals
        res = await client.get("/api/v1/strategy/signals?limit=10")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # Evaluate signals
        res_eval = await client.post("/api/v1/strategy/signals/evaluate?symbol=XAUUSD")
        assert res_eval.status_code == 200
        data = res_eval.json()
        assert "status" in data


@pytest.mark.anyio
async def test_backtest_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Nếu có đủ nến M15 trong DB thì backtest thành công, nếu chưa đủ thì trả về 400
        res = await client.post(
            "/api/v1/strategy/backtest",
            json={"symbol": "XAUUSD", "risk_pct": 1.0, "initial_balance": 10000.0},
        )
        assert res.status_code in (200, 400)
        if res.status_code == 200:
            data = res.json()
            assert "summary" in data
            assert "trades" in data
            assert "equity_curve" in data
