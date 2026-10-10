from datetime import datetime, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.data_ingestion.candle_healer import (
    CandleGapHealer,
    TIMEFRAMES,
    resolve_binance_symbol,
)
from backend.core.models import MarketCandle


def test_resolve_binance_symbol():
    assert resolve_binance_symbol("XAUUSD") == "PAXGUSDT"
    assert resolve_binance_symbol("xau") == "PAXGUSDT"
    assert resolve_binance_symbol("gold") == "PAXGUSDT"
    assert resolve_binance_symbol("BTCUSD") == "BTCUSDT"
    assert resolve_binance_symbol("ETHUSD") == "ETHUSDT"
    assert resolve_binance_symbol("SOLUSDT") == "SOLUSDT"


@pytest.mark.anyio
async def test_detect_trailing_gap():
    healer = CandleGapHealer()
    session = AsyncMock()

    # Giả lập nến mới nhất cách hiện tại 30 phút (trên khung M1)
    old_time = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 1800, timezone.utc)
    mock_candles = [
        datetime.fromtimestamp(old_time.timestamp() - 60 * i, timezone.utc)
        for i in range(350, 0, -1)
    ]
    mock_candles.append(old_time)

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_candles
    session.scalars.return_value = mock_scalars

    gaps = await healer.detect_gaps(session, "XAUUSD", "M1", lookback_hours=24)
    # Phải có ít nhất 1 gap là trailing gap từ old_time + 60s tới now
    assert len(gaps) >= 1
    trailing_gap = gaps[-1]
    assert trailing_gap[0] > old_time


@pytest.mark.anyio
async def test_detect_internal_gaps():
    healer = CandleGapHealer()
    session = AsyncMock()

    base_time = datetime.fromtimestamp(1728000000, timezone.utc)
    # Chuỗi nến có 1 lỗ hổng 10 phút ở giữa
    c1 = base_time
    c2 = datetime.fromtimestamp(base_time.timestamp() + 60, timezone.utc)
    # Lỗ hổng 10 phút (600s)
    c3 = datetime.fromtimestamp(base_time.timestamp() + 660, timezone.utc)
    c4 = datetime.fromtimestamp(base_time.timestamp() + 720, timezone.utc)

    # Thêm nến để đủ > 300 nến
    candles = [datetime.fromtimestamp(base_time.timestamp() - 60 * i, timezone.utc) for i in range(350, 0, -1)]
    candles.extend([c1, c2, c3, c4])

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = candles
    session.scalars.return_value = mock_scalars

    gaps = await healer.detect_gaps(session, "XAUUSD", "M1", lookback_hours=24)
    internal_found = any(gap[0] == datetime.fromtimestamp(c2.timestamp() + 60, timezone.utc) for gap in gaps)
    assert internal_found is True
