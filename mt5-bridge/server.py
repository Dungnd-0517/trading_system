from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query

logger = logging.getLogger("mt5_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="MT5 Linux Data Bridge",
    version="0.3.0",
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

# MT5 timeframe constants mapping (fallback nếu terminal chưa kết nối)
MT5_TF_MAP: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}


def _mt5_timeframe(timeframe: str) -> int:
    """Chuyển đổi chuỗi timeframe (M1, M5...) sang hằng số MT5 TIMEFRAME_*"""
    if terminal is not None:
        tf_map = {
            "M1": getattr(terminal, "TIMEFRAME_M1", 1),
            "M5": getattr(terminal, "TIMEFRAME_M5", 5),
            "M15": getattr(terminal, "TIMEFRAME_M15", 15),
            "H1": getattr(terminal, "TIMEFRAME_H1", 16385),
            "H4": getattr(terminal, "TIMEFRAME_H4", 16388),
            "D1": getattr(terminal, "TIMEFRAME_D1", 16408),
        }
        return tf_map.get(timeframe.upper(), 1)
    return MT5_TF_MAP.get(timeframe.upper(), 1)


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
            logger.info(
                "Successfully connected via mt5linux RPyC to %s:%s (Server: %s, Login: %s)",
                MT5_HOST, MT5_PORT, MT5_SERVER, MT5_LOGIN,
            )
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


@app.post("/reconnect")
def reconnect() -> dict[str, object]:
    """Thử kết nối lại MT5 (hữu ích khi container Wine/MT5 khởi động muộn hơn bridge)"""
    global terminal, connection_error, bridge_mode
    if terminal is not None:
        try:
            terminal.shutdown()
        except Exception:
            pass
        terminal = None
        connection_error = "Reconnecting..."
        bridge_mode = "none"
    success = init_mt5()
    return {
        "success": success,
        "bridge_mode": bridge_mode,
        "error": connection_error if not success else None,
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


@app.get("/candles/{symbol}")
def get_candles(
    symbol: str,
    timeframe: str = Query(default="M1", description="Timeframe: M1, M5, M15, H1, H4, D1"),
    from_date: str = Query(default="2026-01-01", description="Start date in YYYY-MM-DD format (UTC)"),
    count: int = Query(default=1000, ge=1, le=99000, description="Số lượng nến tối đa mỗi lần gọi"),
) -> dict[str, object]:
    """
    Lấy lịch sử nến OHLCV từ MT5 bắt đầu từ from_date.
    Dùng để nạp hoặc làm mới toàn bộ dữ liệu nến từ nguồn MT5 thực.
    """
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)

    try:
        dt_from = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid from_date format: {from_date}. Use YYYY-MM-DD")

    tf_const = _mt5_timeframe(timeframe)

    # Đảm bảo symbol được chọn trong Market Watch
    if not terminal.symbol_select(symbol, True):
        raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

    # Lấy nến từ MT5 bắt đầu từ from_date
    rates = terminal.copy_rates_from(symbol, tf_const, dt_from, count)
    if rates is None:
        err = terminal.last_error()
        raise HTTPException(status_code=503, detail=f"MT5 copy_rates_from failed: {err}")

    candles = []
    for bar in rates:
        candles.append({
            "time": int(bar[0]),        # POSIX timestamp (open_time)
            "open": float(bar[1]),
            "high": float(bar[2]),
            "low": float(bar[3]),
            "close": float(bar[4]),
            "volume": float(bar[5]),    # tick volume
        })

    logger.info(
        "Fetched %d candles for %s %s from %s (MT5 bridge_mode=%s)",
        len(candles), symbol, timeframe, from_date, bridge_mode,
    )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "from_date": from_date,
        "count": len(candles),
        "candles": candles,
    }


@app.get("/candles/{symbol}/latest")
def get_latest_candles(
    symbol: str,
    timeframe: str = Query(default="M1"),
    count: int = Query(default=500, ge=1, le=5000),
) -> dict[str, object]:
    """
    Lấy N nến gần nhất từ MT5 (dùng copy_rates_from_pos với pos=0).
    Dùng để hiển thị biểu đồ 500 nến gần nhất.
    """
    if terminal is None or connection_error:
        raise HTTPException(status_code=503, detail=connection_error)

    tf_const = _mt5_timeframe(timeframe)

    if not terminal.symbol_select(symbol, True):
        raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

    rates = terminal.copy_rates_from_pos(symbol, tf_const, 0, count)
    if rates is None:
        err = terminal.last_error()
        raise HTTPException(status_code=503, detail=f"MT5 copy_rates_from_pos failed: {err}")

    candles = []
    for bar in rates:
        candles.append({
            "time": int(bar[0]),
            "open": float(bar[1]),
            "high": float(bar[2]),
            "low": float(bar[3]),
            "close": float(bar[4]),
            "volume": float(bar[5]),
        })

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }