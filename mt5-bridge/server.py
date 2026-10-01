from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="MT5 Data Bridge", version="0.1.0")
terminal: Any = None
connection_error = "MetaTrader5 runtime is not installed in this container"

try:
    import MetaTrader5 as terminal

    if terminal.initialize():
        connection_error = ""
    else:
        connection_error = str(terminal.last_error())
except ImportError:
    pass


@app.get("/health")
def health() -> dict[str, object]:
    connected = terminal is not None and not connection_error
    return {"status": "ok" if connected else "unavailable", "mt5_connected": connected}


@app.get("/ticks/{symbol}")
def latest_tick(symbol: str) -> dict[str, object]:
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)
    tick = terminal.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No tick available for {symbol}")
    return {
        "symbol": symbol,
        "timestamp": tick.time_msc,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": tick.ask - tick.bid,
        "volume": tick.volume,
    }


@app.get("/ticks/{symbol}/since")
def ticks_since(symbol: str, since_ms: int = Query(default=0, ge=0)) -> dict[str, object]:
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)
    if not terminal.symbol_select(symbol, True):
        raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

    start_ms = since_ms if since_ms > 0 else int((datetime.now(timezone.utc) - timedelta(seconds=2)).timestamp() * 1000)
    start = datetime.fromtimestamp(max(0, start_ms - 1) / 1000, timezone.utc)
    ticks = terminal.copy_ticks_from(symbol, start, 1000, terminal.COPY_TICKS_ALL)
    if ticks is None:
        raise HTTPException(status_code=503, detail=str(terminal.last_error()))

    return {
        "symbol": symbol,
        "ticks": [
            {
                "timestamp": int(tick.time_msc),
                "bid": float(tick.bid),
                "ask": float(tick.ask),
            }
            for tick in ticks
            if int(tick.time_msc) >= start_ms and float(tick.bid) > 0 and float(tick.ask) >= float(tick.bid)
        ],
    }