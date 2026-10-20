from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.data_ingestion.resync_service import (
    clear_candle_cache,
    purge_old_xauusd_candles,
    resync_candles_full,
    trigger_client_chart_refresh,
)


@pytest.mark.anyio
async def test_trigger_client_chart_refresh():
    with patch("backend.data_ingestion.resync_service.redis_client.publish", new_callable=AsyncMock) as mock_pub:
        await trigger_client_chart_refresh("XAUUSD")
        mock_pub.assert_called_once()
        args, _ = mock_pub.call_args
        assert args[0] == "market:ticks"
        assert "REFRESH_CHART" in args[1]
        assert "XAUUSD" in args[1]


@pytest.mark.anyio
async def test_clear_candle_cache():
    async def mock_scan(pattern):
        if "twelve_data" in pattern:
            yield "twelve_data:cache:XAUUSD:1min:500"
        elif "market" in pattern:
            yield "market:candles:XAUUSD"

    with patch("backend.data_ingestion.resync_service.redis_client.scan_iter", side_effect=mock_scan), \
         patch("backend.data_ingestion.resync_service.redis_client.delete", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = 2
        count = await clear_candle_cache()
        assert count == 2
        mock_del.assert_called_once()


@pytest.mark.anyio
async def test_resync_candles_full_filters_closed_hours():
    # Giả lập dữ liệu trả về từ Twelve Data có cả nến trong giờ và ngoài giờ đóng cửa
    mock_candles = [
        # Thứ Sáu 20:00 UTC (Hợp lệ)
        {"time": int(datetime(2026, 10, 9, 20, 0, 0, tzinfo=timezone.utc).timestamp()), "open": 2650.0, "high": 2652.0, "low": 2649.0, "close": 2651.0, "volume": 10.0},
        # Thứ Bảy 12:00 UTC (Thị trường đóng -> Bị loại bỏ)
        {"time": int(datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc).timestamp()), "open": 2651.0, "high": 2651.0, "low": 2651.0, "close": 2651.0, "volume": 0.0},
        # Chủ Nhật 22:00 UTC (Hợp lệ)
        {"time": int(datetime(2026, 10, 11, 22, 0, 0, tzinfo=timezone.utc).timestamp()), "open": 2655.0, "high": 2658.0, "low": 2654.0, "close": 2657.0, "volume": 25.0},
    ]

    with patch("backend.data_ingestion.resync_service.clear_candle_cache", new_callable=AsyncMock) as mock_clear, \
         patch("backend.data_ingestion.resync_service.purge_old_xauusd_candles", new_callable=AsyncMock) as mock_purge, \
         patch("backend.data_ingestion.resync_service.MT5Feed.is_connected", new_callable=AsyncMock, return_value=False), \
         patch("backend.data_ingestion.resync_service.twelve_data_client.fetch_time_series", new_callable=AsyncMock, return_value=mock_candles), \
         patch("backend.data_ingestion.resync_service.trigger_client_chart_refresh", new_callable=AsyncMock) as mock_trigger, \
         patch("backend.data_ingestion.resync_service.session_factory") as mock_session_factory:

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        res = await resync_candles_full("XAUUSD", outputsize_per_tf=500, force_purge=True)

        assert res["status"] == "success"
        assert res["provider"] == "twelvedata"
        mock_clear.assert_called_once()
        mock_purge.assert_called_once()
        mock_trigger.assert_called_once()
        # Đối với mỗi timeframe, chỉ có 2 nến hợp lệ được chèn (nến Thứ Bảy bị loại)
        for tf in ["M1", "M5", "M15", "H1", "H4", "D1"]:
            assert res["seeded_by_timeframe"][tf] == 2
