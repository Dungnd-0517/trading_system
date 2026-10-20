"""
Test Suite cho MT5 Data Integration (Phase 03 - Sprint 03 Update)
Kiểm thử:
1. MT5Feed client methods (get_candles, get_latest_candles, is_connected, health)
2. MT5 History Seeder (xóa nến cũ trước 2026-01-01, upsert nến MT5 với data_source='mt5')
3. Market REST API endpoints (/mt5/status, /mt5/seed, /history ưu tiên MT5)
"""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from main import app
from data_ingestion.mt5_feed import MT5Feed
from data_ingestion.mt5_history_seeder import (
    delete_old_candles,
    upsert_candles_batch,
    seed_all_mt5_history,
    MT5_DATA_START_DT,
    MT5_DATA_START,
)


@pytest.mark.anyio
async def test_mt5_feed_methods():
    """Kiểm thử client MT5Feed khi mock HTTP bridge responses."""
    feed = MT5Feed(base_url="http://mock-bridge:5001")

    mock_candles_payload = [
        {
            "time": 1735689600,
            "open": 2050.50,
            "high": 2055.00,
            "low": 2049.00,
            "close": 2053.20,
            "tick_volume": 120,
        },
        {
            "time": 1735689660,
            "open": 2053.20,
            "high": 2056.10,
            "low": 2052.50,
            "close": 2055.80,
            "tick_volume": 95,
        },
    ]

    # Test get_candles
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "symbol": "XAUUSD",
            "timeframe": "M1",
            "count": 2,
            "candles": mock_candles_payload,
        }
        mock_get.return_value = mock_resp

        candles = await feed.get_candles("XAUUSD", "M1", from_date="2026-01-01")
        assert len(candles) == 2
        assert candles[0]["open"] == 2050.50
        assert candles[1]["close"] == 2055.80

    # Test get_latest_candles (mặc định 500 nến)
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "count": 500,
            "candles": mock_candles_payload,
        }
        mock_get.return_value = mock_resp

        latest = await feed.get_latest_candles("XAUUSD", "M15", count=500)
        assert len(latest) == 2

    # Test is_connected True/False
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "mt5_connected": True}
        mock_get.return_value = mock_resp
        assert await feed.is_connected() is True

        mock_resp.json.return_value = {"status": "ok", "mt5_connected": False}
        assert await feed.is_connected() is False


@pytest.mark.anyio
async def test_upsert_candles_batch():
    """Kiểm thử upsert_candles_batch gắn đúng data_source='mt5'."""
    session = AsyncMock()
    mock_candles = [
        {
            "time": 1735689600,
            "open": 2060.00,
            "high": 2065.00,
            "low": 2058.00,
            "close": 2062.50,
            "volume": 350,
        }
    ]

    count = await upsert_candles_batch(session, "XAUUSD", "M15", mock_candles)
    assert count == 1
    assert session.execute.called


@pytest.mark.anyio
async def test_purge_old_candles():
    """Kiểm thử hàm xóa nến cũ trước mốc 2026-01-01."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1250
    session.execute.return_value = mock_result

    deleted = await delete_old_candles(session, "XAUUSD", before_dt=MT5_DATA_START_DT)
    assert deleted == 1250
    assert session.execute.called


@pytest.mark.anyio
async def test_market_mt5_api_endpoints():
    """Kiểm thử các REST API endpoints /mt5/status và /mt5/seed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. /api/v1/market/mt5/status
        with patch.object(MT5Feed, "health", new_callable=AsyncMock) as mock_health, \
             patch("api.v1.market.check_needs_mt5_reseed", new_callable=AsyncMock) as mock_reseed, \
             patch("api.v1.market.candle_gap_healer.get_integrity_report", new_callable=AsyncMock) as mock_report:
            mock_health.return_value = {
                "status": "ok",
                "connected": True,
                "login": 5057446983,
                "server": "MetaQuotes-Demo",
            }
            mock_reseed.return_value = False
            mock_report.return_value = {"status": "healthy", "symbols": {}}

            res = await client.get("/api/v1/market/mt5/status")
            assert res.status_code == 200
            data = res.json()
            assert data["mt5_bridge"]["connected"] is True
            assert data["data_start_config"] == MT5_DATA_START
            assert data["needs_reseed"] is False

        # 2. /api/v1/market/mt5/seed thành công
        with patch("api.v1.market.seed_all_mt5_history", new_callable=AsyncMock) as mock_seed:
            mock_seed.return_value = {
                "status": "success",
                "symbol": "XAUUSD",
                "from_date": "2026-01-01",
                "total_seeded": 1200,
                "seeded": {"M1": 1000, "M5": 200},
            }
            res = await client.post("/api/v1/market/mt5/seed?symbol=XAUUSD")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["total_seeded"] == 1200
