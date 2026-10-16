from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query

logger = logging.getLogger("mt5_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="MT5 Linux Data Bridge",
    version="0.2.0",
    description="Real-time MetaTrader 5 Bridge connecting MetaQuotes-Demo via mt5linux (Wine/RPyC) or native Windows runtime.",
)

# Configuration from environment with MetaQuotes-Demo defaults
MT5_LOGIN = os.getenv("MT5_LOGIN", "5057446983")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "FxN@6nZf")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
MT5_HOST = os.getenv("MT5_HOST", "localhost")
MT5_PORT = int(os.getenv("MT5_PORT", "18812"))

terminal: Any = None
connection_error: str = "MetaTrader5 runtime is not initialized"
bridge_mode: str = "none"


def init_mt5() -> bool:
    global terminal, connection_error, bridge_mode
    login_int = int(MT5_LOGIN) if str(MT5_LOGIN).isdigit() else 0

    # 1. First attempt: Official native MetaTrader5 (Windows Host)
    try:
        import MetaTrader5 as native_mt5  # type: ignore

        if native_mt5.initialize(login=login_int, password=MT5_PASSWORD, server=MT5_SERVER):
            terminal = native_mt5
            connection_error = ""
            bridge_mode = "native_windows"
            logger.info("Successfully connected via native MetaTrader5 to %s (Login: %s)", MT5_SERVER, MT5_LOGIN)
            return True
        else:
            err = native_mt5.last_error()
            connection_error = f"Native MT5 initialize failed: {err}"
            logger.warning(connection_error)
    except (ImportError, Exception) as exc:
        logger.debug("Native MetaTrader5 not available: %s", exc)

    # 2. Second attempt: mt5linux bridge (Linux Wine / RPyC bridge container)
    try:
        from mt5linux import MetaTrader5 as MT5Linux  # type: ignore

        rpc_client = MT5Linux(host=MT5_HOST, port=MT5_PORT)
        if rpc_client.initialize(login=login_int, password=MT5_PASSWORD, server=MT5_SERVER):
            terminal = rpc_client
            connection_error = ""
            bridge_mode = "mt5linux_rpyc"
            logger.info("Successfully connected via mt5linux RPyC to %s:%s (Server: %s, Login: %s)", MT5_HOST, MT5_PORT, MT5_SERVER, MT5_LOGIN)
            return True
        else:
            err = rpc_client.last_error()
            connection_error = f"mt5linux initialize failed: {err}"
            logger.warning(connection_error)
    except (ImportError, Exception) as exc:
        connection_error = f"mt5linux connection failed: {exc}"
        logger.debug(connection_error)

    return False


# Attempt initialization at module load
init_mt5()


@app.get("/health")
def health() -> dict[str, object]:
    connected = terminal is not None and not connection_error
    return {
        "status": "ok" if connected else "unavailable",
        "mt5_connected": connected,
        "bridge_mode": bridge_mode,
        "server": MT5_SERVER,
        "login": MT5_LOGIN,
        "error": connection_error if not connected else None,
    }


@app.get("/account")
def account_info() -> dict[str, object]:
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)
    info = terminal.account_info()
    if info is None:
        raise HTTPException(status_code=503, detail="Failed to retrieve MT5 account info")
    return {
        "login": getattr(info, "login", MT5_LOGIN),
        "name": getattr(info, "name", "Nguyen Dinh Dung"),
        "server": getattr(info, "server", MT5_SERVER),
        "currency": getattr(info, "currency", "USD"),
        "balance": float(getattr(info, "balance", 0.0)),
        "equity": float(getattr(info, "equity", 0.0)),
        "margin": float(getattr(info, "margin", 0.0)),
        "margin_free": float(getattr(info, "margin_free", 0.0)),
        "margin_level": float(getattr(info, "margin_level", 0.0)),
        "leverage": int(getattr(info, "leverage", 100)),
    }


@app.get("/ticks/{symbol}")
def latest_tick(symbol: str) -> dict[str, object]:
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)
    tick = terminal.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No tick available for {symbol}")
    return {
        "symbol": symbol,
        "timestamp": int(tick.time_msc),
        "bid": float(tick.bid),
        "ask": float(tick.ask),
        "spread": float(tick.ask - tick.bid),
        "volume": float(getattr(tick, "volume", 1.0)),
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