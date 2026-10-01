import numpy as np
import pandas as pd

from backend.ai_engine import sessions, smc
from backend.simulation.risk_checker import SymbolSpec, lot_size


def synth(n=3000, seed=1, start="2024-01-01"):
    rng = np.random.default_rng(seed)
    close = 2000 + np.cumsum(rng.normal(0, 1.2, n))
    open_ = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.normal(0, 0.6, (n, 2)))
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wick[:, 0],
                         "low": np.minimum(open_, close) - wick[:, 1], "close": close}, index=idx)


def test_no_lookahead():
    df = synth()
    full = smc.market_structure(df)
    for k in (500, 1200, 2500):
        part = smc.market_structure(df.iloc[:k])
        ref = full[full["idx"] < k].reset_index(drop=True)
        assert part[["idx", "type", "dir"]].equals(ref[["idx", "type", "dir"]]), k
    f_full = smc.fair_value_gaps(df)
    f_part = smc.fair_value_gaps(df.iloc[:1000])
    assert f_part[["idx", "dir", "top", "bottom"]].equals(
        f_full[f_full["idx"] < 1000][["idx", "dir", "top", "bottom"]].reset_index(drop=True))


def test_bos_choch_semantics():
    df = synth()
    ev = smc.market_structure(df)
    assert len(ev) > 20
    trend = 0
    for r in ev.itertuples():
        expect = "CHOCH" if (trend != 0 and r.dir != trend) else "BOS"
        assert r.type == expect
        trend = r.dir


def test_zones_and_sweeps():
    df = synth()
    ev = smc.market_structure(df)
    ob = smc.order_blocks(df, ev)
    assert len(ob) > 0 and (ob["top"] >= ob["bottom"]).all()
    assert len(smc.liquidity_sweeps(df)) > 0


def test_sessions_dst():
    # 07:00 NY: mùa đông = 12:00 UTC, mùa hè = 11:00 UTC
    assert sessions.in_kill_zone("2024-01-10 12:00", ("ny_am",))
    assert not sessions.in_kill_zone("2024-01-10 11:00", ("ny_am",))
    assert sessions.in_kill_zone("2024-07-10 11:00", ("ny_am",))


def test_lot_size():
    spec = SymbolSpec()
    lots = lot_size(10000, 0.5, 2000.0, 1995.0, spec)  # rủi ro $50, SL 5$ => 500 tick x $1 = $500/lot => 0.10
    assert abs(lots - 0.10) < 1e-9


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("OK", name)
