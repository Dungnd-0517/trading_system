import asyncio
from datetime import datetime, timezone
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.data_ingestion.twelve_data_client import (
    TwelveDataClient,
    TwelveDataRateLimiter,
    resolve_twelve_data_symbol,
    parse_twelve_data_timestamp,
    TIMEFRAME_TO_TWELVE_DATA,
)


def test_symbol_mapping():
    assert resolve_twelve_data_symbol("XAUUSD") == "XAU/USD"
    assert resolve_twelve_data_symbol("xau") == "XAU/USD"
    assert resolve_twelve_data_symbol("GOLD") == "XAU/USD"
    assert resolve_twelve_data_symbol("PAXG") == "XAU/USD"
    assert resolve_twelve_data_symbol("PAXGUSDT") == "XAU/USD"
    assert resolve_twelve_data_symbol("EURUSD") == "EUR/USD"
    assert resolve_twelve_data_symbol("GBPUSD") == "GBP/USD"
    assert resolve_twelve_data_symbol("XAU/USD") == "XAU/USD"


def test_timeframe_mapping():
    assert TIMEFRAME_TO_TWELVE_DATA["M1"] == "1min"
    assert TIMEFRAME_TO_TWELVE_DATA["M5"] == "5min"
    assert TIMEFRAME_TO_TWELVE_DATA["M15"] == "15min"
    assert TIMEFRAME_TO_TWELVE_DATA["H1"] == "1h"
    assert TIMEFRAME_TO_TWELVE_DATA["H4"] == "4h"
    assert TIMEFRAME_TO_TWELVE_DATA["D1"] == "1day"


def test_timestamp_parsing():
    # Intraday: "YYYY-MM-DD HH:MM:SS"
    ts1 = parse_twelve_data_timestamp("2026-10-17 14:30:00")
    dt1 = datetime.fromtimestamp(ts1, timezone.utc)
    assert dt1.year == 2026
    assert dt1.month == 10
    assert dt1.day == 17
    assert dt1.hour == 14
    assert dt1.minute == 30
    assert dt1.second == 0

    # Daily: "YYYY-MM-DD"
    ts2 = parse_twelve_data_timestamp("2026-10-17")
    dt2 = datetime.fromtimestamp(ts2, timezone.utc)
    assert dt2.year == 2026
    assert dt2.month == 10
    assert dt2.day == 17
    assert dt2.hour == 0
    assert dt2.minute == 0


@pytest.mark.anyio
async def test_rate_limiter_in_memory_tracking():
    limiter = TwelveDataRateLimiter(max_per_minute=3, max_per_day=10)

    # Mock redis to fail so it uses in-memory tracking
    with patch("backend.data_ingestion.twelve_data_client.redis_client.pipeline", side_effect=Exception("Redis down")):
        for _ in range(3):
            await limiter.acquire()

        usage = await limiter.get_usage()
        assert usage["minute_usage"] == 3
        assert usage["daily_usage"] == 3


@pytest.mark.anyio
async def test_fetch_time_series_chronological_ordering():
    client = TwelveDataClient(api_key="test_key")

    mock_raw_response = {
        "status": "ok",
        "values": [
            {
                "datetime": "2026-10-16 10:02:00",
                "open": "2730.0",
                "high": "2732.0",
                "low": "2729.0",
                "close": "2731.0",
                "volume": "150",
            },
            {
                "datetime": "2026-10-16 10:01:00",
                "open": "2728.0",
                "high": "2730.5",
                "low": "2727.5",
                "close": "2730.0",
                "volume": "120",
            },
            {
                "datetime": "2026-10-16 10:00:00",
                "open": "2725.0",
                "high": "2728.5",
                "low": "2725.0",
                "close": "2728.0",
                "volume": "100",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_raw_response

    mock_limiter = AsyncMock()
    client.limiter = mock_limiter

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        candles = await client.fetch_time_series(
            symbol="XAUUSD",
            timeframe="M1",
            outputsize=3,
            use_cache=False,
        )

        assert len(candles) == 3
        # Must be in chronological order (oldest first: 10:00 -> 10:01 -> 10:02)
        assert candles[0]["time"] < candles[1]["time"] < candles[2]["time"]
        assert candles[0]["open"] == 2725.0
        assert candles[2]["close"] == 2731.0


@pytest.mark.anyio
async def test_fetch_time_series_cache_hit():
    client = TwelveDataClient(api_key="test_key")

    cached_candles = [
        {"time": 1792000000, "open": 2700.0, "high": 2705.0, "low": 2698.0, "close": 2703.0, "volume": 50.0}
    ]

    with patch(
        "backend.data_ingestion.twelve_data_client.redis_client.get",
        new_callable=AsyncMock,
        return_value=json.dumps(cached_candles).encode("utf-8"),
    ):
        result = await client.fetch_time_series(
            symbol="XAUUSD",
            timeframe="M1",
            outputsize=1,
            use_cache=True,
        )
        assert len(result) == 1
        assert result[0]["close"] == 2703.0
