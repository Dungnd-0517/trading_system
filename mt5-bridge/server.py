from datetime import datetime, timedelta, timezone
import json
import logging
import os
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
import rpyc

logger = logging.getLogger("mt5_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="MT5 Linux Data Bridge",
    version="0.3.4",
    description="Real-time MetaTrader 5 Bridge connecting MetaQuotes-Demo via mt5linux (Wine/RPyC) or native Windows runtime.",
)

# Configuration from environment with MetaQuotes-Demo defaults
MT5_LOGIN = os.getenv("MT5_LOGIN", "5057446983")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "FxN@6nZf")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
MT5_HOST = os.getenv("MT5_HOST", "mt5-wine-server")
MT5_PORT = int(os.getenv("MT5_PORT", "18812"))

terminal: Any = None
connection_error: str = "MetaTrader5 runtime is not initialized"
bridge_mode: str = "none"
rpyc_conn: Any = None
mt5_lock = threading.Lock()

# MT5 timeframe constants mapping
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


def _get_remote_datetime(dt: datetime) -> Any:
    """Chuyển đổi datetime sang remote datetime nếu dùng RPyC."""
    if rpyc_conn is not None:
        r_dt = rpyc_conn.modules["datetime"].datetime
        r_tz = rpyc_conn.modules["datetime"].timezone
        return r_dt.fromtimestamp(dt.timestamp(), r_tz.utc)
    return dt


def init_mt5() -> bool:
    global terminal, connection_error, bridge_mode, rpyc_conn
    with mt5_lock:
        login_int = int(MT5_LOGIN) if str(MT5_LOGIN).isdigit() else 0

        # 1. Native MetaTrader5 (Windows Host)
        try:
            import MetaTrader5 as native_mt5  # type: ignore

            connected_native = False
            if login_int and MT5_PASSWORD:
                connected_native = bool(native_mt5.initialize(login=login_int, password=MT5_PASSWORD, server=MT5_SERVER))
            if not connected_native:
                connected_native = bool(native_mt5.initialize())

            if connected_native:
                terminal = native_mt5
                connection_error = ""
                bridge_mode = "native_windows"
                rpyc_conn = None
                logger.info("Successfully connected via native MetaTrader5 to %s (Login: %s)", MT5_SERVER, MT5_LOGIN)
                return True
            else:
                err = native_mt5.last_error()
                connection_error = f"Native MT5 initialize failed: {err}"
                logger.warning(connection_error)
        except (ImportError, Exception) as exc:
            logger.debug("Native MetaTrader5 not available: %s", exc)

        # 2. RPyC Classic direct connection (mt5-wine-server container)
        try:
            logger.info("Connecting to MT5 Wine server via RPyC at %s:%s...", MT5_HOST, MT5_PORT)
            conn = rpyc.classic.connect(MT5_HOST, MT5_PORT)
            conn.execute("""
import json
def parse_ticks_json(ticks, start_ms):
    if ticks is None:
        return '[]'
    res = []
    for t in ticks:
        tm = int(t['time_msc'])
        b = float(t['bid'])
        a = float(t['ask'])
        if tm >= start_ms and b > 0 and a >= b:
            res.append({'timestamp': tm, 'bid': b, 'ask': a})
    return json.dumps(res)

def get_candles_range_or_pos(symbol, tf_const, dt_from_ts, count):
    import MetaTrader5 as mt5
    from datetime import datetime, timezone
    dt1 = datetime.fromtimestamp(dt_from_ts, timezone.utc)
    dt2 = datetime.now(timezone.utc)
    
    # 1. Thử copy_rates_range từ dt1 đến hiện tại
    rates = mt5.copy_rates_range(symbol, tf_const, dt1, dt2)
    
    # 2. Nếu copy_rates_range không có dữ liệu (do lịch sử chưa load đủ sâu), fallback sang copy_rates_from_pos
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, min(count, 50000))
        if rates is not None:
            rates = [r for r in rates if r[0] >= dt_from_ts]
            
    if rates is None:
        return '[]'
        
    res = []
    for bar in rates:
        res.append({
            'time': int(bar[0]),
            'open': float(bar[1]),
            'high': float(bar[2]),
            'low': float(bar[3]),
            'close': float(bar[4]),
            'volume': float(bar[5]),
        })
    return json.dumps(res)

def parse_candles_json(rates):
    if rates is None:
        return '[]'
    res = []
    for bar in rates:
        res.append({
            'time': int(bar[0]),
            'open': float(bar[1]),
            'high': float(bar[2]),
            'low': float(bar[3]),
            'close': float(bar[4]),
            'volume': float(bar[5]),
        })
    return json.dumps(res)
""")
            mt5_module = conn.modules["MetaTrader5"]

            connected_rpyc = False
            if login_int and MT5_PASSWORD:
                connected_rpyc = bool(mt5_module.initialize(login=login_int, password=MT5_PASSWORD, server=MT5_SERVER))
            if not connected_rpyc:
                connected_rpyc = bool(mt5_module.initialize())

            if connected_rpyc:
                terminal = mt5_module
                rpyc_conn = conn
                connection_error = ""
                bridge_mode = "mt5linux_rpyc"
                logger.info(
                    "Successfully connected via RPyC to %s:%s (Server: %s, Login: %s)",
                    MT5_HOST, MT5_PORT, MT5_SERVER, MT5_LOGIN,
                )
                return True
            else:
                err = mt5_module.last_error()
                connection_error = f"MT5 initialize over RPyC failed: {err}"
                logger.warning(connection_error)
        except Exception as exc:
            connection_error = f"RPyC connect to {MT5_HOST}:{MT5_PORT} failed: {exc}"
            logger.warning(connection_error)

        return False


# Attempt initialization at module load
init_mt5()


def _background_reconnect_worker() -> None:
    """Luồng nền tự động kết nối lại MT5 nếu bị ngắt kết nối hoặc mt5-wine-server khởi động trễ."""
    while True:
        try:
            time.sleep(5)
            with mt5_lock:
                connected = terminal is not None and not connection_error
            if not connected:
                logger.info("MT5 disconnected or not initialized. Auto-reconnecting in background...")
                init_mt5()
        except Exception as exc:
            logger.debug("Background auto-reconnect error: %s", exc)


threading.Thread(target=_background_reconnect_worker, daemon=True, name="mt5_auto_reconnect").start()


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
    """Thử kết nối lại MT5."""
    global terminal, connection_error, bridge_mode, rpyc_conn
    with mt5_lock:
        if terminal is not None:
            try:
                terminal.shutdown()
            except Exception:
                pass
            terminal = None
            rpyc_conn = None
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
    with mt5_lock:
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
    with mt5_lock:
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

    with mt5_lock:
        if not terminal.symbol_select(symbol, True):
            raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

        start_ms = since_ms if since_ms > 0 else int((datetime.now(timezone.utc) - timedelta(seconds=2)).timestamp() * 1000)
        start_dt = datetime.fromtimestamp(max(0, start_ms - 1) / 1000, timezone.utc)

        if rpyc_conn is not None:
            remote_dt = _get_remote_datetime(start_dt)
            ticks = terminal.copy_ticks_from(symbol, remote_dt, 1000, terminal.COPY_TICKS_ALL)
            if ticks is None:
                raise HTTPException(status_code=503, detail=str(terminal.last_error()))
            parse_ticks_json = rpyc_conn.namespace["parse_ticks_json"]
            raw_json = str(parse_ticks_json(ticks, start_ms))
            parsed_ticks = json.loads(raw_json)
        else:
            ticks = terminal.copy_ticks_from(symbol, start_dt, 1000, terminal.COPY_TICKS_ALL)
            if ticks is None:
                raise HTTPException(status_code=503, detail=str(terminal.last_error()))
            parsed_ticks = [
                {
                    "timestamp": int(tick.time_msc),
                    "bid": float(tick.bid),
                    "ask": float(tick.ask),
                }
                for tick in ticks
                if int(tick.time_msc) >= start_ms and float(tick.bid) > 0 and float(tick.ask) >= float(tick.bid)
            ]

    return {
        "symbol": symbol,
        "ticks": parsed_ticks,
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
    dt_from_ts = int(dt_from.timestamp())

    with mt5_lock:
        if not terminal.symbol_select(symbol, True):
            raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

        if rpyc_conn is not None:
            get_candles_fn = rpyc_conn.namespace["get_candles_range_or_pos"]
            raw_json = str(get_candles_fn(symbol, tf_const, dt_from_ts, count))
            candles = json.loads(raw_json)
        else:
            rates = terminal.copy_rates_from(symbol, tf_const, dt_from, count)
            if rates is None:
                err = terminal.last_error()
                raise HTTPException(status_code=503, detail=f"MT5 copy_rates_from failed: {err}")
            candles = [
                {
                    "time": int(bar[0]),
                    "open": float(bar[1]),
                    "high": float(bar[2]),
                    "low": float(bar[3]),
                    "close": float(bar[4]),
                    "volume": float(bar[5]),
                }
                for bar in rates
            ]

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

    with mt5_lock:
        if not terminal.symbol_select(symbol, True):
            raise HTTPException(status_code=404, detail=f"Unknown MT5 symbol: {symbol}")

        rates = terminal.copy_rates_from_pos(symbol, tf_const, 0, count)
        if rates is None:
            err = terminal.last_error()
            raise HTTPException(status_code=503, detail=f"MT5 copy_rates_from_pos failed: {err}")

        if rpyc_conn is not None:
            parse_candles_json = rpyc_conn.namespace["parse_candles_json"]
            raw_json = str(parse_candles_json(rates))
            candles = json.loads(raw_json)
        else:
            candles = [
                {
                    "time": int(bar[0]),
                    "open": float(bar[1]),
                    "high": float(bar[2]),
                    "low": float(bar[3]),
                    "close": float(bar[4]),
                    "volume": float(bar[5]),
                }
                for bar in rates
            ]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }