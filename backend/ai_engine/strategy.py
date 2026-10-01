"""
Chiến lược đa khung: D1/H4 (bias) -> H1 (POI: OB/FVG trong Discount/Premium) -> M15 (tap POI + CHoCH) trong Kill Zone.
frames: dict[str, DataFrame] chỉ chứa NẾN ĐÃ ĐÓNG, cột open/high/low/close, index UTC (thời điểm mở nến).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from . import smc, sessions

MIN_BARS = {"M15": 60, "H1": 60, "H4": 40, "D1": 30}


@dataclass
class Signal:
    time: pd.Timestamp
    side: str          # "long" | "short"
    entry: float
    sl: float
    tp: float
    rr: float
    reason: str


def htf_bias(frames: dict, cfg: dict) -> int:
    L, R = cfg["swing_left"], cfg["swing_right"]
    out = []
    for tf in ("H4", "D1"):
        ev = smc.market_structure(frames[tf], L, R)
        out.append(int(ev["dir"].iloc[-1]) if len(ev) else 0)
    b4, b1 = out
    if cfg.get("require_d1_alignment", True):
        return b4 if b4 == b1 else 0
    return b4


def find_pois(h1: pd.DataFrame, bias: int, cfg: dict) -> list:
    L, R = cfg["swing_left"], cfg["swing_right"]
    ev = smc.market_structure(h1, L, R)
    obs = smc.order_blocks(h1, ev)
    fvg = smc.fair_value_gaps(h1, cfg["fvg_min_atr"])
    hi, lo = smc.dealing_range(h1, L, R)
    eq = (hi + lo) / 2
    n = len(h1)
    zones = []
    for kind, z in (("OB", obs), ("FVG", fvg)):
        for r in z.itertuples():
            if r.dir != bias or r.invalid_idx >= 0 or n - r.idx > cfg["poi_max_age_h1"]:
                continue
            mid = (r.top + r.bottom) / 2
            if (bias == 1 and mid > eq) or (bias == -1 and mid < eq):
                continue  # long chỉ ở Discount, short chỉ ở Premium
            zones.append((kind, float(r.top), float(r.bottom), int(r.idx)))
    zones.sort(key=lambda x: -x[3])  # mới nhất trước
    return zones


def generate_signal(frames: dict, cfg: dict) -> Signal | None:
    for tf, m in MIN_BARS.items():
        if len(frames[tf]) < m:
            return None
    m15 = frames["M15"]
    now = m15.index[-1] + pd.Timedelta(minutes=15)  # thời điểm nến M15 vừa đóng
    if not sessions.in_kill_zone(now, cfg["kill_zones"]):
        return None

    bias = htf_bias(frames, cfg)
    if bias == 0:
        return None

    # --- trigger M15: MSS vừa xảy ra ở nến cuối, đúng hướng bias
    e15 = smc.market_structure(m15, cfg["m15_swing"], cfg["m15_swing"])
    if not len(e15) or int(e15["idx"].iloc[-1]) != len(m15) - 1 or int(e15["dir"].iloc[-1]) != bias:
        return None
    if cfg["require_choch"] and e15["type"].iloc[-1] != "CHOCH":
        return None

    recent = m15.iloc[-cfg["tap_lookback_m15"]:]
    a15 = float(smc.atr(m15).iloc[-1])
    entry = float(m15["close"].iloc[-1])
    h1 = frames["H1"]

    for kind, top, bottom, _ in find_pois(h1, bias, cfg):
        if bias == 1:
            tapped = recent["low"].min() <= top and recent["close"].min() > bottom
        else:
            tapped = recent["high"].max() >= bottom and recent["close"].max() < top
        if not tapped:
            continue

        buf = cfg["sl_buffer_atr"] * a15
        if bias == 1:
            sl = min(float(recent["low"].min()), bottom) - buf
        else:
            sl = max(float(recent["high"].max()), top) + buf
        risk = abs(entry - sl)
        if risk <= 0 or risk > cfg["max_risk_atr15"] * a15:
            continue

        highs, lows = smc.swing_levels(h1, cfg["swing_left"], cfg["swing_right"])
        if bias == 1:
            need = entry + cfg["min_rr"] * risk
            c = highs[highs >= need]
            tp = float(c.min()) if len(c) else entry + cfg["default_rr"] * risk
        else:
            need = entry - cfg["min_rr"] * risk
            c = lows[lows <= need]
            tp = float(c.max()) if len(c) else entry - cfg["default_rr"] * risk
        rr = abs(tp - entry) / risk
        side = "long" if bias == 1 else "short"
        reason = f"{side} | D1/H4 bias | H1 {kind} [{bottom:.2f}-{top:.2f}] | M15 CHoCH | KZ"
        return Signal(now, side, entry, sl, tp, rr, reason)
    return None
