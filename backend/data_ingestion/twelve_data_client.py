import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import random
import time
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert

from core.config import settings
from core.database import session_factory
from core.models import MarketCandle
from core.redis_client import client as redis_client
from data_ingestion.market_hours import is_xauusd_trading_hour

logger = logging.getLogger(__name__)

# Standard timeframe mappings to Twelve Data intervals
TIMEFRAME_TO_TWELVE_DATA = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1day",
}

TWELVE_DATA_TO_TIMEFRAME = {v: k for k, v in TIMEFRAME_TO_TWELVE_DATA.items()}

# Cache TTL by timeframe (guaranteed >= 60s as required)
CACHE_TTL_SECONDS = {
    "M1": 60,       # 1 minute minimum
    "M5": 120,      # 2 minutes
    "M15": 300,     # 5 minutes
    "H1": 600,      # 10 minutes
    "H4": 1800,     # 30 minutes
    "D1": 3600,     # 1 hour
}

TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}


def resolve_twelve_data_symbol(symbol: str) -> str:
    """Map system symbols to Twelve Data format.
    Twelve Data requires Spot Gold to be XAU/USD.
    """
    sym = (symbol or "XAUUSD").upper().strip()
    if sym in {"XAUUSD", "XAU", "GOLD", "PAXG", "PAXGUSDT"}:
        return "XAU/USD"
    if "/" in sym:
        return sym
    if len(sym) == 6:
        return f"{sym[:3]}/{sym[3:]}"
    return sym


def parse_twelve_data_datetime(dt_str: str) -> datetime:
    """Parse Twelve Data datetime string into UTC datetime.
    Twelve Data intraday format: 'YYYY-MM-DD HH:MM:SS'
    Twelve Data daily format: 'YYYY-MM-DD'
    """
    clean_str = dt_str.strip()
    if " " in clean_str:
        return datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return datetime.strptime(clean_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def parse_twelve_data_timestamp(dt_str: str) -> int:
    """Parse Twelve Data datetime string into UTC Unix timestamp in seconds."""
    return int(parse_twelve_data_datetime(dt_str).timestamp())


class TwelveDataRateLimiter:
    """Quản lý Giới hạn Gọi API (Rate Limit Handler):
    - Hạn ngạch: Max 8 requests / phút và 800 requests / ngày.
    - Sử dụng Redis để quản lý tập trung và đồng bộ giữa các workers.
    - Tự động fallback in-memory nếu Redis tạm thời gián đoạn.
    """

    def __init__(self, max_per_minute: int = 8, max_per_day: int = 800) -> None:
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self._mem_minute_counts: dict[int, int] = {}
        self._mem_daily_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Đảm bảo không vượt quá hạn ngạch 8 req/phút và 800 req/ngày.
        Nếu đạt giới hạn phút, chờ đến chu kỳ phút tiếp theo.
        Nếu đạt giới hạn ngày, ném lỗi quota.
        """
        async with self._lock:
            while True:
                now = time.time()
                minute_key = int(now // 60)
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                redis_ok = False
                minute_count = 0
                daily_count = 0

                try:
                    r_min_key = f"twelve_data:quota:min:{minute_key}"
                    r_day_key = f"twelve_data:quota:day:{today_str}"

                    # Pipeline check & increment
                    pipe = redis_client.pipeline()
                    pipe.get(r_min_key)
                    pipe.get(r_day_key)
                    results = await pipe.execute()

                    minute_count = int(results[0]) if results[0] else 0
                    daily_count = int(results[1]) if results[1] else 0
                    redis_ok = True
                except Exception as exc:
                    logger.debug("Redis rate limiter check fallback to in-memory: %s", exc)
                    minute_count = self._mem_minute_counts.get(minute_key, 0)
                    daily_count = self._mem_daily_counts.get(today_str, 0)

                # Check daily quota
                if daily_count >= self.max_per_day:
                    msg = f"Twelve Data daily quota limit exceeded ({daily_count}/{self.max_per_day} requests for {today_str})"
                    logger.error(msg)
                    raise RuntimeError(msg)

                # Check minute quota
                if minute_count >= self.max_per_minute:
                    sleep_secs = 60 - (now % 60) + 0.5
                    logger.warning(
                        "Twelve Data minute rate limit reached (%d/%d reqs). Backing off for %.2fs...",
                        minute_count,
                        self.max_per_minute,
                        sleep_secs,
                    )
                    await asyncio.sleep(sleep_secs)
                    continue

                # Record request
                if redis_ok:
                    try:
                        pipe = redis_client.pipeline()
                        pipe.incr(r_min_key)
                        pipe.expire(r_min_key, 90)
                        pipe.incr(r_day_key)
                        pipe.expire(r_day_key, 172800)  # 2 days
                        await pipe.execute()
                    except Exception as exc:
                        logger.debug("Redis incr failed: %s", exc)
                        self._mem_minute_counts[minute_key] = minute_count + 1
                        self._mem_daily_counts[today_str] = daily_count + 1
                else:
                    self._mem_minute_counts[minute_key] = minute_count + 1
                    self._mem_daily_counts[today_str] = daily_count + 1

                # Clean old in-memory counts
                old_mins = [m for m in self._mem_minute_counts if m < minute_key - 5]
                for m in old_mins:
                    self._mem_minute_counts.pop(m, None)
                break

    async def get_usage(self) -> dict[str, Any]:
        """Lấy thông số sử dụng hạn ngạch hiện tại"""
        now = time.time()
        minute_key = int(now // 60)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            r_min_key = f"twelve_data:quota:min:{minute_key}"
            r_day_key = f"twelve_data:quota:day:{today_str}"
            pipe = redis_client.pipeline()
            pipe.get(r_min_key)
            pipe.get(r_day_key)
            results = await pipe.execute()
            min_used = int(results[0]) if results[0] else 0
            day_used = int(results[1]) if results[1] else 0
        except Exception:
            min_used = self._mem_minute_counts.get(minute_key, 0)
            day_used = self._mem_daily_counts.get(today_str, 0)

        return {
            "minute_usage": min_used,
            "minute_limit": self.max_per_minute,
            "daily_usage": day_used,
            "daily_limit": self.max_per_day,
            "date": today_str,
        }


# Global singleton rate limiter
rate_limiter = TwelveDataRateLimiter(max_per_minute=8, max_per_day=800)


class TwelveDataClient:
    """Client kết nối Twelve Data API cho Spot Gold (XAU/USD):
    - Tích hợp Rate Limit Handler (8 req/min, 800 req/day).
    - Tích hợp Retry + Exponential Backoff.
    - Tích hợp Redis Caching (TTL tối thiểu 60s).
    - Chuẩn hóa định dạng thời gian Unix timestamp khớp biểu đồ frontend.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        limiter: TwelveDataRateLimiter | None = None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "twelve_data_api_key", "d1d845408648474cb09a52607e38e184")
        self.base_url = (base_url or getattr(settings, "twelve_data_base_url", "https://api.twelvedata.com")).rstrip("/")
        self.limiter = limiter or rate_limiter

    async def fetch_time_series(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "M1",
        outputsize: int = 500,
        start_date: str | None = None,
        end_date: str | None = None,
        use_cache: bool = True,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Truy xuất chuỗi nến lịch sử từ Twelve Data API:
        1. Kiểm tra cache Redis nếu use_cache=True.
        2. Nếu cache miss: xin quota từ RateLimiter.
        3. Thực thi HTTP GET với cơ chế Retry + Exponential Backoff.
        4. Chuẩn hóa nến theo thứ tự thời gian tăng dần và lưu cache Redis.
        """
        td_symbol = resolve_twelve_data_symbol(symbol)
        td_interval = TIMEFRAME_TO_TWELVE_DATA.get(timeframe.upper(), "1min")
        ttl = max(60, CACHE_TTL_SECONDS.get(timeframe.upper(), 60))

        # Cache key
        cache_key = (
            f"twelve_data:cache:{td_symbol}:{td_interval}:{outputsize}:"
            f"{start_date or 'latest'}:{end_date or 'latest'}"
        )

        if use_cache:
            try:
                cached_bytes = await redis_client.get(cache_key)
                if cached_bytes:
                    data = json.loads(cached_bytes.decode("utf-8") if isinstance(cached_bytes, bytes) else cached_bytes)
                    logger.debug("Twelve Data cache HIT: %s (%d candles)", cache_key, len(data))
                    return data
            except Exception as exc:
                logger.debug("Redis cache read error: %s", exc)

        # Build request parameters
        params: dict[str, Any] = {
            "symbol": td_symbol,
            "interval": td_interval,
            "outputsize": min(outputsize, 5000),
            "timezone": "UTC",
            "apikey": self.api_key,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        endpoint = f"{self.base_url}/time_series"
        last_error: Exception | None = None

        for attempt in range(max_retries):
            # Tuân thủ hạn ngạch Rate Limit
            await self.limiter.acquire()

            try:
                async with httpx.AsyncClient(timeout=15.0) as http:
                    resp = await http.get(endpoint, params=params)

                # Xử lý HTTP 429 Too Many Requests
                if resp.status_code == 429:
                    backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                    logger.warning(
                        "Twelve Data HTTP 429 Rate Limit (attempt %d/%d). Backing off for %.2fs...",
                        attempt + 1,
                        max_retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                # Xử lý lỗi server 5xx
                if resp.status_code >= 500:
                    backoff = (2 ** attempt) + random.uniform(0.2, 0.8)
                    logger.warning(
                        "Twelve Data HTTP %d Server Error (attempt %d/%d). Backing off for %.2fs...",
                        resp.status_code,
                        attempt + 1,
                        max_retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                if resp.status_code != 200:
                    logger.error(
                        "Twelve Data HTTP %d Error: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return []

                payload = resp.json()

                # Twelve Data có thể trả về status: "error" với mã 429 hoặc lỗi khác
                if payload.get("status") == "error":
                    code = payload.get("code")
                    message = payload.get("message", "")
                    if code == 429:
                        backoff = (2 ** attempt) + random.uniform(1.0, 2.5)
                        logger.warning(
                            "Twelve Data JSON 429 Rate Limit: %s. Backoff %.2fs...",
                            message,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    logger.error("Twelve Data API Error [%s]: %s", code, message)
                    return []

                raw_values = payload.get("values", [])
                if not isinstance(raw_values, list) or not raw_values:
                    logger.warning("Twelve Data returned empty values for %s %s", td_symbol, td_interval)
                    return []

                # Chuẩn hóa định dạng thời gian và chuyển đổi để khớp biểu đồ frontend
                # Twelve Data trả nến mới nhất trước (descending) -> đảo ngược sang tăng dần (ascending)
                parsed_candles: list[dict[str, Any]] = []
                for item in reversed(raw_values):
                    try:
                        dt = parse_twelve_data_datetime(item["datetime"])
                        ts_seconds = int(dt.timestamp())
                        # Lọc bỏ các nến rơi vào khung giờ đóng cửa của XAUUSD
                        if symbol.upper() in {"XAUUSD", "XAU/USD", "XAU", "GOLD"} and not is_xauusd_trading_hour(ts_seconds):
                            continue
                        parsed_candles.append({
                            "time": ts_seconds,
                            "open_time": dt.isoformat(),
                            "open": float(item["open"]),
                            "high": float(item["high"]),
                            "low": float(item["low"]),
                            "close": float(item["close"]),
                            "volume": float(item.get("volume") or 0.0),
                            "data_source": "twelvedata",
                        })
                    except Exception as parse_err:
                        logger.debug("Failed to parse Twelve Data candle item %s: %s", item, parse_err)
                        continue

                # Lưu vào cache Redis
                if use_cache and parsed_candles:
                    try:
                        await redis_client.set(
                            cache_key,
                            json.dumps(parsed_candles, separators=(",", ":")),
                            ex=ttl,
                        )
                        logger.debug("Saved %d candles to Twelve Data cache (%s, TTL=%ds)", len(parsed_candles), cache_key, ttl)
                    except Exception as cache_err:
                        logger.debug("Failed to save to Redis cache: %s", cache_err)

                return parsed_candles

            except (httpx.TransportError, httpx.TimeoutException) as net_err:
                last_error = net_err
                backoff = (2 ** attempt) + random.uniform(0.5, 1.0)
                logger.warning(
                    "Twelve Data network error on attempt %d/%d: %s. Retrying in %.2fs...",
                    attempt + 1,
                    max_retries,
                    net_err,
                    backoff,
                )
                await asyncio.sleep(backoff)
            except Exception as exc:
                last_error = exc
                logger.error("Twelve Data request error on attempt %d: %s", attempt + 1, exc)
                break

        if last_error:
            logger.error("Twelve Data all %d retries exhausted: %s", max_retries, last_error)
        return []

    async def get_latest_candle(
        self, symbol: str = "XAUUSD", timeframe: str = "M1"
    ) -> dict[str, Any] | None:
        """Lấy nến gần nhất phục vụ kiểm tra realtime fallback"""
        candles = await self.fetch_time_series(
            symbol=symbol,
            timeframe=timeframe,
            outputsize=2,
            use_cache=False,
        )
        return candles[-1] if candles else None

    async def seed_candles_to_database(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "M1",
        outputsize: int = 500,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """Nạp dữ liệu nến từ Twelve Data API vào Database (MarketCandle)"""
        candles = await self.fetch_time_series(
            symbol=symbol,
            timeframe=timeframe,
            outputsize=outputsize,
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
        )
        if not candles:
            return 0

        total_upserted = 0
        try:
            async with session_factory() as session:
                for c in candles:
                    ot = datetime.fromtimestamp(c["time"], timezone.utc)
                    values = {
                        "symbol": symbol.upper(),
                        "timeframe": timeframe.upper(),
                        "open_time": ot,
                        "open": Decimal(str(c["open"])),
                        "high": Decimal(str(c["high"])),
                        "low": Decimal(str(c["low"])),
                        "close": Decimal(str(c["close"])),
                        "volume": Decimal(str(c.get("volume", 0.0))),
                        "data_source": "twelvedata",
                    }
                    stmt = insert(MarketCandle).values(**values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["symbol", "timeframe", "open_time"],
                        set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                    )
                    await session.execute(stmt)
                    total_upserted += 1
                await session.commit()
            logger.info(
                "Successfully seeded %d candles for %s %s from Twelve Data API (data_source=twelvedata)",
                total_upserted,
                symbol,
                timeframe,
            )
        except Exception as exc:
            logger.error("Failed to persist Twelve Data candles to DB: %s", exc)

        return total_upserted


# Global singleton Twelve Data Client
twelve_data_client = TwelveDataClient()
