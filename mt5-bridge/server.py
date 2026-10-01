from typing import Any

from fastapi import FastAPI, HTTPException

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