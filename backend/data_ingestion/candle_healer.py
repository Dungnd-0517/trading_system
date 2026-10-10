import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import logging
import time
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_factory
from core.models import MarketCandle

logger = logging.getLogger(__name__)

TIMEFRAMES = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}

TIMEFRAME_TO_BINANCE_INTERVAL = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

BINANCE_API_URLS = [
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
]


def resolve_binance_symbol(symbol: str) -> str:
    sym = symbol.upper()
    if sym in {"XAUUSD", "XAU", "GOLD", "PAXG", "PAXGUSDT"}:
        return "PAXGUSDT"
    if sym in {"BTCUSD", "BTC", "BTCUSDT"}:
        return "BTCUSDT"
    if sym in {"ETHUSD", "ETH", "ETHUSDT"}:
        return "ETHUSDT"
    if not sym.endswith("USDT"):
        return f"{sym}USDT"
    return sym


class CandleGapHealer:
    """
    Hệ thống phát hiện khoảng trống dữ liệu nến (Gaps) và tự động bù đắp (Healer)
    đảm bảo dữ liệu liên tục 24/7 trên tất cả các khung thời gian khi server downtime.
    """

    def __init__(self) -> None:
        self.is_healing = False
        self.last_check_at: datetime | None = None
        self.last_healed_at: datetime | None = None
        self.total_healed_bars = 0
        self.status_summary: dict[str, Any] = {}

    async def detect_gaps(
        self,
        session: AsyncSession,
        symbol: str = "XAUUSD",
        timeframe: str = "M1",
        lookback_hours: int = 168,  # Mặc định quét trong 7 ngày gần nhất
    ) -> list[tuple[datetime, datetime]]:
        """
        Phát hiện các khoảng trống (gaps) trong chuỗi nến của một khung thời gian:
        1. Khoảng trống phía sau (Trailing/Head gap): từ nến mới nhất trong DB tới hiện tại.
        2. Khoảng trống nội bộ (Internal gaps): các đoạn đứt gãy giữa 2 nến liên tiếp.
        3. Khoảng trống phía trước (Leading gap): nếu tổng số nến < 500 nến tối thiểu.
        """
        interval_secs = TIMEFRAMES.get(timeframe, 60)
        now_utc = datetime.now(timezone.utc)
        since_time = now_utc.timestamp() - (lookback_hours * 3600)
        since_dt = datetime.fromtimestamp(since_time, timezone.utc)

        # Lấy danh sách timestamp các nến trong khoảng lookback
        query = (
            select(MarketCandle.open_time)
            .where(
                MarketCandle.symbol == symbol,
                MarketCandle.timeframe == timeframe,
                MarketCandle.open_time >= since_dt,
            )
            .order_by(MarketCandle.open_time.asc())
        )
        rows = (await session.scalars(query)).all()
        gaps: list[tuple[datetime, datetime]] = []

        if not rows:
            # Nếu chưa có nến nào trong khoảng lookback, cần nạp toàn bộ
            gaps.append((since_dt, now_utc))
            return gaps

        # 1. Kiểm tra Trailing Gap (từ nến mới nhất tới hiện tại)
        latest_time = rows[-1]
        trailing_diff = (now_utc - latest_time).total_seconds()
        # Cho phép dung sai 1.5 chu kỳ nến
        if trailing_diff >= interval_secs * 1.5:
            # Gap bắt đầu từ chu kỳ kế tiếp của latest_time
            gap_start = datetime.fromtimestamp(latest_time.timestamp() + interval_secs, timezone.utc)
            gaps.append((gap_start, now_utc))

        # 2. Kiểm tra Internal Gaps (đứt gãy giữa các nến)
        for i in range(len(rows) - 1):
            curr_time = rows[i]
            next_time = rows[i + 1]
            diff = (next_time - curr_time).total_seconds()
            if diff >= interval_secs * 1.5:
                # Có nến bị thiếu ở giữa
                gap_start = datetime.fromtimestamp(curr_time.timestamp() + interval_secs, timezone.utc)
                gap_end = datetime.fromtimestamp(next_time.timestamp() - interval_secs, timezone.utc)
                if gap_start <= gap_end:
                    gaps.append((gap_start, gap_end))

        # 3. Kiểm tra Leading Gap nếu tổng nến quá ít (< 300 nến)
        if len(rows) < 300:
            oldest_time = rows[0]
            target_history_start = datetime.fromtimestamp(
                oldest_time.timestamp() - (300 - len(rows)) * interval_secs,
                timezone.utc,
            )
            gaps.insert(0, (target_history_start, oldest_time))

        return gaps

    async def fetch_binance_klines_chunk(
        self,
        http: httpx.AsyncClient,
        binance_symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int | None = None,
        limit: int = 1000,
    ) -> list[list[Any]]:
        """Gọi Binance REST API lấy một mẻ nến klines tối đa 1000 nến"""
        params: dict[str, Any] = {
            "symbol": binance_symbol,
            "interval": interval,
            "startTime": start_ms,
            "limit": limit,
        }
        if end_ms is not None:
            params["endTime"] = end_ms

        for base_url in BINANCE_API_URLS:
            try:
                resp = await http.get(base_url, params=params, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                elif resp.status_code == 429:
                    logger.warning("Binance rate limit 429 hit, back off")
                    await asyncio.sleep(2)
            except Exception as exc:
                logger.debug("Binance API %s failed: %s", base_url, exc)
                continue
        return []

    async def heal_range(
        self,
        session: AsyncSession,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        http: httpx.AsyncClient,
    ) -> int:
        """Bù đắp nến trong khoảng [start_time, end_time] từ Binance REST API"""
        interval = TIMEFRAME_TO_BINANCE_INTERVAL.get(timeframe)
        if not interval:
            return 0

        binance_sym = resolve_binance_symbol(symbol)
        step_secs = TIMEFRAMES[timeframe]
        step_ms = step_secs * 1000

        curr_start_ms = int(start_time.timestamp() * 1000)
        target_end_ms = int(end_time.timestamp() * 1000)
        total_upserted = 0

        while curr_start_ms <= target_end_ms:
            klines = await self.fetch_binance_klines_chunk(
                http=http,
                binance_symbol=binance_sym,
                interval=interval,
                start_ms=curr_start_ms,
                end_ms=target_end_ms,
                limit=1000,
            )
            if not klines:
                break

            for item in klines:
                open_time_ms = int(item[0])
                open_time = datetime.fromtimestamp(open_time_ms / 1000, timezone.utc)
                values = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "open_time": open_time,
                    "open": Decimal(str(item[1])),
                    "high": Decimal(str(item[2])),
                    "low": Decimal(str(item[3])),
                    "close": Decimal(str(item[4])),
                    "volume": Decimal(str(item[5])),
                }
                stmt = insert(MarketCandle).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "timeframe", "open_time"],
                    set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                )
                await session.execute(stmt)
                total_upserted += 1

            await session.commit()

            last_returned_ms = int(klines[-1][0])
            next_start_ms = last_returned_ms + step_ms
            if next_start_ms <= curr_start_ms:
                # Tránh vòng lặp vô tận
                curr_start_ms += 1000 * step_ms
            else:
                curr_start_ms = next_start_ms

            if len(klines) < 1000:
                # Đã lấy hết dữ liệu tới thời điểm hiện tại
                break

        return total_upserted

    async def synthesize_higher_timeframes_from_m1(
        self,
        session: AsyncSession,
        symbol: str = "XAUUSD",
    ) -> dict[str, int]:
        """Tổng hợp các khung thời gian cao hơn (M5, M15, H1, H4, D1) từ nến M1 nội bộ nếu cần"""
        results: dict[str, int] = {}
        for tf in ["M5", "M15", "H1", "H4", "D1"]:
            seconds = TIMEFRAMES[tf]
            try:
                # Lấy 2000 nến M1 gần nhất
                m1_rows = (
                    await session.scalars(
                        select(MarketCandle)
                        .where(MarketCandle.symbol == symbol, MarketCandle.timeframe == "M1")
                        .order_by(MarketCandle.open_time.asc())
                        .limit(3000)
                    )
                ).all()
                if not m1_rows:
                    continue

                buckets: dict[int, dict[str, Any]] = {}
                for row in m1_rows:
                    sec = int(row.open_time.timestamp())
                    b_sec = sec - (sec % seconds)
                    if b_sec not in buckets:
                        buckets[b_sec] = {
                            "open_time": datetime.fromtimestamp(b_sec, timezone.utc),
                            "open": row.open,
                            "high": row.high,
                            "low": row.low,
                            "close": row.close,
                            "volume": row.volume,
                        }
                    else:
                        b = buckets[b_sec]
                        b["high"] = max(b["high"], row.high)
                        b["low"] = min(b["low"], row.low)
                        b["close"] = row.close
                        b["volume"] += row.volume

                for b in buckets.values():
                    values = {
                        "symbol": symbol,
                        "timeframe": tf,
                        "open_time": b["open_time"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                    }
                    stmt = insert(MarketCandle).values(**values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["symbol", "timeframe", "open_time"],
                        set_={k: v for k, v in values.items() if k not in {"symbol", "timeframe", "open_time"}},
                    )
                    await session.execute(stmt)
                await session.commit()
                results[tf] = len(buckets)
            except Exception as exc:
                logger.warning("Synthesis error for %s %s: %s", symbol, tf, exc)
        return results

    async def check_and_heal_all(
        self,
        symbol: str = "XAUUSD",
        lookback_hours: int = 168,
    ) -> dict[str, Any]:
        """
        Quét toàn diện tất cả các khung thời gian và bù đắp toàn bộ nến bị thiếu.
        """
        if self.is_healing:
            return {"status": "in_progress", "healed": {}}

        self.is_healing = True
        healed_summary: dict[str, int] = {}
        now_utc = datetime.now(timezone.utc)
        self.last_check_at = now_utc

        try:
            timeout = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
                async with session_factory() as session:
                    # Duyệt qua từng khung thời gian theo thứ tự từ nhỏ tới lớn
                    for tf in ["M1", "M5", "M15", "H1", "H4", "D1"]:
                        gaps = await self.detect_gaps(
                            session=session,
                            symbol=symbol,
                            timeframe=tf,
                            lookback_hours=lookback_hours,
                        )
                        tf_healed = 0
                        if gaps:
                            logger.info(
                                "Detected %d gap intervals in %s %s (lookback: %dh). Healing...",
                                len(gaps),
                                symbol,
                                tf,
                                lookback_hours,
                            )
                            for gap_start, gap_end in gaps:
                                count = await self.heal_range(
                                    session=session,
                                    symbol=symbol,
                                    timeframe=tf,
                                    start_time=gap_start,
                                    end_time=gap_end,
                                    http=http,
                                )
                                tf_healed += count

                        healed_summary[tf] = tf_healed

                    # Kiểm tra và đồng bộ trạng thái sức khỏe của từng khung
                    await self._update_status_summary(session, symbol)

            total = sum(healed_summary.values())
            if total > 0:
                self.last_healed_at = datetime.now(timezone.utc)
                self.total_healed_bars += total
                logger.info(
                    "CandleGapHealer complete for %s. Total bars healed: %d. Breakdown: %s",
                    symbol,
                    total,
                    healed_summary,
                )

            return {
                "status": "success",
                "healed": healed_summary,
                "total_healed": total,
                "checked_at": now_utc.isoformat(),
            }
        except Exception as exc:
            logger.exception("Error during CandleGapHealer run: %s", exc)
            return {"status": "error", "error": str(exc), "healed": healed_summary}
        finally:
            self.is_healing = False

    async def _update_status_summary(self, session: AsyncSession, symbol: str) -> None:
        """Cập nhật bản tóm tắt tình trạng liên tục của từng khung thời gian"""
        now_utc = datetime.now(timezone.utc)
        summary: dict[str, Any] = {}

        for tf, secs in TIMEFRAMES.items():
            row = await session.execute(
                select(
                    func.count(MarketCandle.id),
                    func.min(MarketCandle.open_time),
                    func.max(MarketCandle.open_time),
                ).where(MarketCandle.symbol == symbol, MarketCandle.timeframe == tf)
            )
            count, oldest, newest = row.first() or (0, None, None)
            minutes_behind = (
                round((now_utc - newest).total_seconds() / 60.0, 1)
                if newest
                else None
            )
            is_synced = bool(newest and (now_utc - newest).total_seconds() < secs * 2.0)

            summary[tf] = {
                "count": count,
                "oldest": oldest.isoformat() if oldest else None,
                "newest": newest.isoformat() if newest else None,
                "minutes_behind": minutes_behind,
                "is_synced": is_synced,
            }

        self.status_summary = summary

    async def get_integrity_report(self, symbol: str = "XAUUSD") -> dict[str, Any]:
        """Báo cáo tình trạng tính toàn vẹn và liên tục của nến"""
        if not self.status_summary:
            async with session_factory() as session:
                await self._update_status_summary(session, symbol)

        all_synced = all(info.get("is_synced", False) for info in self.status_summary.values())
        return {
            "symbol": symbol,
            "overall_status": "HEALTHY" if all_synced else "GAPS_DETECTED",
            "is_healing": self.is_healing,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "last_healed_at": self.last_healed_at.isoformat() if self.last_healed_at else None,
            "total_healed_bars": self.total_healed_bars,
            "timeframes": self.status_summary,
        }


candle_gap_healer = CandleGapHealer()


class CandleIntegrityWorker:
    """Worker chạy nền tự động kiểm tra và bù nến định kỳ và khi phục hồi downtime"""

    def __init__(self, check_interval_secs: int = 60) -> None:
        self.check_interval_secs = check_interval_secs
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("CandleIntegrityWorker started. Initializing startup gap healing...")

        # 1. Chạy ngay khi server khởi động lại (Startup Recovery)
        try:
            await asyncio.sleep(2)  # Đợi DB kết nối hoàn tất
            res = await candle_gap_healer.check_and_heal_all(symbol="XAUUSD", lookback_hours=168)
            logger.info("Startup gap healing finished: %s", res.get("healed"))
        except Exception as exc:
            logger.warning("Startup gap healing encountered an issue: %s", exc)

        # 2. Vòng lặp định kỳ (Periodic Background Monitor)
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_secs)
                if not self._running:
                    break

                # Kiểm tra xem có khung nào bị trễ nến không
                report = await candle_gap_healer.get_integrity_report("XAUUSD")
                tfs = report.get("timeframes", {})
                needs_healing = any(not info.get("is_synced", True) for info in tfs.values())

                if needs_healing:
                    logger.info("CandleIntegrityWorker detected stale/missing candles. Triggering healing...")
                    await candle_gap_healer.check_and_heal_all(symbol="XAUUSD", lookback_hours=24)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("CandleIntegrityWorker loop exception: %s", exc)
                await asyncio.sleep(10)

    def stop(self) -> None:
        self._running = False


candle_integrity_worker = CandleIntegrityWorker(check_interval_secs=60)
