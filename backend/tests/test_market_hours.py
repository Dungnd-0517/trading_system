from datetime import datetime, timezone
import pytest

from backend.data_ingestion.market_hours import (
    is_xauusd_trading_hour,
    is_xauusd_market_closed,
    filter_valid_xauusd_candles,
    is_natural_market_break,
)


def test_trading_hours_regular_day():
    # Thứ Ba 10:00 UTC -> Mở
    tue_10am = datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(tue_10am) is True
    assert is_xauusd_market_closed(tue_10am) is False

    # Thứ Tư 15:30 UTC -> Mở
    wed_afternoon = datetime(2026, 10, 7, 15, 30, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(wed_afternoon) is True


def test_trading_hours_daily_break():
    # Thứ Ba 21:00 UTC -> Đóng (Daily break)
    tue_21_00 = datetime(2026, 10, 6, 21, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(tue_21_00) is False
    assert is_xauusd_market_closed(tue_21_00) is True

    # Thứ Ba 21:45 UTC -> Đóng
    tue_21_45 = datetime(2026, 10, 6, 21, 45, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(tue_21_45) is False

    # Thứ Ba 22:00 UTC -> Mở lại
    tue_22_00 = datetime(2026, 10, 6, 22, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(tue_22_00) is True


def test_trading_hours_weekend():
    # Thứ Sáu 20:59 UTC -> Mở
    fri_20_59 = datetime(2026, 10, 9, 20, 59, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(fri_20_59) is True

    # Thứ Sáu 21:00 UTC -> Bắt đầu đóng phiên cuối tuần
    fri_21_00 = datetime(2026, 10, 9, 21, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(fri_21_00) is False

    # Thứ Sáu 22:30 UTC -> Đóng
    fri_22_30 = datetime(2026, 10, 9, 22, 30, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(fri_22_30) is False

    # Thứ Bảy 12:00 UTC -> Đóng cả ngày
    sat_noon = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(sat_noon) is False

    # Chủ Nhật 15:00 UTC -> Đóng
    sun_15_00 = datetime(2026, 10, 11, 15, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(sun_15_00) is False

    # Chủ Nhật 21:59 UTC -> Đóng
    sun_21_59 = datetime(2026, 10, 11, 21, 59, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(sun_21_59) is False

    # Chủ Nhật 22:00 UTC -> Mở cửa tuần mới!
    sun_22_00 = datetime(2026, 10, 11, 22, 0, 0, tzinfo=timezone.utc)
    assert is_xauusd_trading_hour(sun_22_00) is True


def test_filter_valid_xauusd_candles():
    candles = [
        {"time": int(datetime(2026, 10, 9, 20, 0, 0, tzinfo=timezone.utc).timestamp()), "close": 2650.0},
        {"time": int(datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc).timestamp()), "close": 2650.0},  # T7 -> Loại
        {"time": int(datetime(2026, 10, 11, 22, 0, 0, tzinfo=timezone.utc).timestamp()), "close": 2655.0},  # CN 22h -> Giữ
    ]
    valid = filter_valid_xauusd_candles(candles)
    assert len(valid) == 2
    assert valid[0]["close"] == 2650.0
    assert valid[1]["close"] == 2655.0


def test_is_natural_market_break():
    # Gap cuối tuần: Thứ 6 21:00 UTC đến Chủ Nhật 22:00 UTC
    fri_close = datetime(2026, 10, 9, 21, 0, 0, tzinfo=timezone.utc)
    sun_open = datetime(2026, 10, 11, 22, 0, 0, tzinfo=timezone.utc)
    assert is_natural_market_break(fri_close, sun_open) is True

    # Gap trong ngày Thứ 3: 10:00 UTC đến 14:00 UTC (có giờ giao dịch) -> False (Lỗ hổng dữ liệu thật)
    tue_10am = datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc)
    tue_2pm = datetime(2026, 10, 6, 14, 0, 0, tzinfo=timezone.utc)
    assert is_natural_market_break(tue_10am, tue_2pm) is False
