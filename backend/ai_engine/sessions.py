"""Kill zones theo giờ New York (chuẩn ICT). zoneinfo tự xử lý DST."""
from zoneinfo import ZoneInfo
import pandas as pd

NY = ZoneInfo("America/New_York")

# (giờ bắt đầu, giờ kết thúc) theo giờ NY
KILL_ZONES = {
    "asia": (20, 24),
    "london": (2, 5),
    "ny_am": (7, 10),
    "ny_pm": (13.5, 16),
}
SILVER_BULLET = [(3, 4), (10, 11), (14, 15)]


def ny_time(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(NY)


def _in(h: float, a: float, b: float) -> bool:
    return (a <= h < b) if a < b else (h >= a or h < b)


def in_kill_zone(ts, zones=("london", "ny_am")) -> bool:
    t = ny_time(ts)
    h = t.hour + t.minute / 60
    return any(_in(h, *KILL_ZONES[z]) for z in zones)


def in_silver_bullet(ts) -> bool:
    t = ny_time(ts)
    h = t.hour + t.minute / 60
    return any(_in(h, a, b) for a, b in SILVER_BULLET)
