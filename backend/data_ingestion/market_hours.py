"""
XAUUSD Market Hours and Trading Session Validator
=================================================
Định nghĩa và quản lý khung giờ hoạt động chuẩn của Vàng giao ngay (Spot Gold XAU/USD).

Quy tắc phiên giao dịch:
1. Cuối tuần (Weekend Break):
   - Tạm dừng ghi nến từ 21:00 UTC Thứ Sáu (04:00 AM T7 VN) đến 22:00 UTC Chủ Nhật (05:00 AM T2 VN).
   - Thứ Sáu (weekday=4): đóng từ 21:00 UTC trở đi.
   - Thứ Bảy (weekday=5): đóng cả ngày.
   - Chủ Nhật (weekday=6): đóng cho đến 22:00 UTC (mở phiên lúc 22:00 UTC).
2. Nghỉ phiên ngày (Daily Break):
   - Không tạo nến trong khoảng 21:00 UTC - 22:00 UTC hàng ngày (Thứ Hai đến Thứ Năm, và áp dụng chung cho tất cả các ngày).
"""

from datetime import datetime, timezone
from typing import Any


def to_utc_datetime(dt_or_ts: datetime | int | float) -> datetime:
    """Chuyển đổi datetime hoặc timestamp thành UTC datetime chuẩn."""
    if isinstance(dt_or_ts, (int, float)):
        return datetime.fromtimestamp(dt_or_ts, timezone.utc)
    if dt_or_ts.tzinfo is None:
        return dt_or_ts.replace(tzinfo=timezone.utc)
    return dt_or_ts.astimezone(timezone.utc)


def is_xauusd_trading_hour(dt_or_ts: datetime | int | float) -> bool:
    """
    Kiểm tra xem thời điểm dt_or_ts có thuộc khung giờ giao dịch hợp lệ của XAUUSD hay không.
    Trả về True nếu thị trường ĐANG MỞ, False nếu ĐANG NGHỈ/ĐÓNG CỬA.
    """
    dt = to_utc_datetime(dt_or_ts)
    weekday = dt.weekday()  # Monday=0, Tuesday=1, ..., Friday=4, Saturday=5, Sunday=6
    hour = dt.hour

    # 1. Cuối tuần (Weekend)
    # Thứ Sáu: đóng từ 21:00 UTC
    if weekday == 4 and hour >= 21:
        return False

    # Thứ Bảy: đóng toàn bộ 24h
    if weekday == 5:
        return False

    # Chủ Nhật: đóng trước 22:00 UTC (mở lại từ 22:00 UTC)
    if weekday == 6 and hour < 22:
        return False

    # 2. Nghỉ phiên ngày (Daily Break: 21:00 - 22:00 UTC hàng ngày)
    if hour == 21:
        return False

    return True


def is_xauusd_market_closed(dt_or_ts: datetime | int | float) -> bool:
    """Kiểm tra xem thời điểm có đang trong thời gian thị trường đóng cửa hay không."""
    return not is_xauusd_trading_hour(dt_or_ts)


def filter_valid_xauusd_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Lọc và loại bỏ các nến xuất hiện trong khung giờ thị trường đóng cửa (weekend hoặc daily break).
    Đảm bảo không lưu nến doji giả hoặc tick rác vào DB.
    """
    valid: list[dict[str, Any]] = []
    for c in candles:
        t = c.get("time") or c.get("open_time")
        if t is None:
            continue
        if is_xauusd_trading_hour(t):
            valid.append(c)
    return valid


def is_natural_market_break(start_dt: datetime, end_dt: datetime) -> bool:
    """
    Kiểm tra xem khoảng trống giữa start_dt và end_dt có phải là khoảng nghỉ phiên tự nhiên
    (Weekend gap hoặc Daily break gap) hay không.
    Nếu toàn bộ khoảng trống này hoàn toàn nằm trong khung giờ đóng cửa, đây KHÔNG PHẢI lỗi thiếu dữ liệu.
    """
    start_utc = to_utc_datetime(start_dt)
    end_utc = to_utc_datetime(end_dt)

    # Nếu start_dt >= end_dt thì không có gap
    if start_utc >= end_utc:
        return True

    # Kiểm tra xem có bất kỳ thời điểm nào trong khoảng (start_utc, end_utc) thuộc giờ giao dịch không
    # Quét từng bước nhảy 15 phút
    curr_ts = int(start_utc.timestamp()) + 60
    end_ts = int(end_utc.timestamp())

    step = 900  # 15 phút
    while curr_ts < end_ts:
        if is_xauusd_trading_hour(curr_ts):
            # Có thời gian thị trường mở nhưng bị thiếu nến -> Không phải nghỉ phiên hoàn toàn
            return False
        curr_ts += step

    # Kiểm tra điểm cuối
    if end_ts > int(start_utc.timestamp()) and is_xauusd_trading_hour(end_ts - 1):
        return False

    return True
