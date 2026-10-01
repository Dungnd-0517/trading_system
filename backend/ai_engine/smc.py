"""
Nguyên thủy SMC/ICT dạng rule-based, KHÔNG look-ahead.

Định nghĩa (ghi rõ để backtest lặp lại được):
- Swing high/low: fractal (left, right). Chỉ được xác nhận sau `right` nến.
- BOS/CHoCH: nến ĐÓNG CỬA vượt swing gần nhất.
    BOS   = cùng hướng xu hướng hiện tại; CHOCH = ngược hướng xu hướng hiện tại.
- FVG: 3 nến, gap giữa nến 1 và nến 3 >= min_atr x ATR.
- Order Block: nến ngược hướng cuối cùng tại đáy/đỉnh của chặng displacement gây ra BOS/CHoCH.
- Liquidity sweep: quét qua swing nhưng ĐÓNG CỬA quay lại bên trong.
- Zone bị "invalid" khi có nến đóng cửa xuyên qua cạnh xa của zone.
Cột idx/touched_idx/invalid_idx là vị trí nguyên (positional); -1 = chưa xảy ra.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def swing_flags(df: pd.DataFrame, left: int = 3, right: int = 3):
    """Cờ swing tại vị trí j (đã dùng đủ `right` nến sau j -> không look-ahead nếu chỉ dùng khi j <= i-right)."""
    w = left + right + 1
    hi = df["high"].rolling(w).max().shift(-right)
    lo = df["low"].rolling(w).min().shift(-right)
    return (df["high"] == hi).to_numpy(), (df["low"] == lo).to_numpy()


def swing_levels(df: pd.DataFrame, left: int = 3, right: int = 3):
    fh, fl = swing_flags(df, left, right)
    return df["high"].to_numpy()[fh], df["low"].to_numpy()[fl]


def dealing_range(df: pd.DataFrame, left: int = 3, right: int = 3):
    fh, fl = swing_flags(df, left, right)
    hi = df["high"].to_numpy()[fh]
    lo = df["low"].to_numpy()[fl]
    return (hi[-1] if len(hi) else df["high"].max()), (lo[-1] if len(lo) else df["low"].min())


def premium_discount(price: float, hi: float, lo: float) -> str:
    return "discount" if price < (hi + lo) / 2 else "premium"


def market_structure(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    fh, fl = swing_flags(df, left, right)
    sh = sl = None
    trend = 0
    rows = []
    for i in range(len(df)):
        j = i - right
        if j >= left:
            if fh[j]:
                sh = (h[j], j)
            if fl[j]:
                sl = (l[j], j)
        if sh is not None and c[i] > sh[0]:
            kind = "CHOCH" if trend == -1 else "BOS"
            rows.append(dict(idx=i, time=df.index[i], type=kind, dir=1, level=sh[0], swing_idx=sh[1]))
            trend, sh = 1, None
        elif sl is not None and c[i] < sl[0]:
            kind = "CHOCH" if trend == 1 else "BOS"
            rows.append(dict(idx=i, time=df.index[i], type=kind, dir=-1, level=sl[0], swing_idx=sl[1]))
            trend, sl = -1, None
    return pd.DataFrame(rows, columns=["idx", "time", "type", "dir", "level", "swing_idx"])


def _track(h, l, c, start, top, bottom, d):
    touched = invalid = -1
    for k in range(start, len(h)):
        if touched < 0 and l[k] <= top and h[k] >= bottom:
            touched = k
        if (d == 1 and c[k] < bottom) or (d == -1 and c[k] > top):
            invalid = k
            break
    return touched, invalid


def fair_value_gaps(df: pd.DataFrame, min_atr: float = 0.3) -> pd.DataFrame:
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    a = atr(df).to_numpy()
    rows = []
    for i in range(2, len(df)):
        if l[i] > h[i - 2] and (l[i] - h[i - 2]) >= min_atr * a[i]:
            top, bottom, d = l[i], h[i - 2], 1
        elif h[i] < l[i - 2] and (l[i - 2] - h[i]) >= min_atr * a[i]:
            top, bottom, d = l[i - 2], h[i], -1
        else:
            continue
        t, v = _track(h, l, c, i + 1, top, bottom, d)
        rows.append(dict(idx=i, time=df.index[i], dir=d, top=top, bottom=bottom, touched_idx=t, invalid_idx=v))
    return pd.DataFrame(rows, columns=["idx", "time", "dir", "top", "bottom", "touched_idx", "invalid_idx"])


def order_blocks(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rows = []
    for e in events.itertuples():
        s, i, d = int(e.swing_idx), int(e.idx), int(e.dir)
        if i <= s:
            continue
        if d == 1:
            k = s + int(np.argmin(l[s:i + 1]))
            cand = [b for b in range(k, max(k - 6, -1), -1) if c[b] < o[b]]
        else:
            k = s + int(np.argmax(h[s:i + 1]))
            cand = [b for b in range(k, max(k - 6, -1), -1) if c[b] > o[b]]
        if not cand:
            continue
        m = cand[0]
        top, bottom = h[m], l[m]
        t, v = _track(h, l, c, i + 1, top, bottom, d)
        rows.append(dict(idx=m, time=df.index[m], event_idx=i, dir=d, top=top, bottom=bottom,
                         touched_idx=t, invalid_idx=v))
    return pd.DataFrame(rows, columns=["idx", "time", "event_idx", "dir", "top", "bottom", "touched_idx", "invalid_idx"])


def liquidity_sweeps(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    fh, fl = swing_flags(df, left, right)
    lh = ll = None
    rows = []
    for i in range(len(df)):
        j = i - right
        if j >= left:
            if fh[j]:
                lh = h[j]
            if fl[j]:
                ll = l[j]
        if lh is not None and h[i] > lh:
            if c[i] < lh:
                rows.append(dict(idx=i, time=df.index[i], dir=-1, level=lh, extreme=h[i]))
            lh = None
        if ll is not None and l[i] < ll:
            if c[i] > ll:
                rows.append(dict(idx=i, time=df.index[i], dir=1, level=ll, extreme=l[i]))
            ll = None
    return pd.DataFrame(rows, columns=["idx", "time", "dir", "level", "extreme"])
