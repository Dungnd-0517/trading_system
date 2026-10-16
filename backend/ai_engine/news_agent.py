import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import logging
import math
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.news_guard import news_circuit_breaker
from core.config import settings
from core.database import session_factory
from core.models import EconomicEvent, FinancialNews, SystemTradingConfig
from core.redis_client import client as redis_client
from data_ingestion.news_sources import (
    parse_fair_economy_calendar,
    parse_rss_feed,
)

logger = logging.getLogger(__name__)

# Kênh Redis Pub/Sub chuẩn cho sự kiện News Agent
REDIS_CHANNEL_NEWS_AGENT = "agent:news:event"
REDIS_CHANNEL_CIRCUIT_BREAKER = "market:circuit_breaker"

# Từ khóa Breaking News khẩn cấp tác động mạnh đến Vàng (XAUUSD)
_BREAKING_KEYWORDS = [
    re.compile(r"\b(war|invasion|conflict|missile|attack|military|middle east|escalat\w*)\b", re.I),
    re.compile(r"\b(emergency rate|unscheduled meeting|flash crash|bank failure|default)\b", re.I),
    re.compile(r"\b(nuclear|sanction\w*|embargo|martial law|geopolitical crisis)\b", re.I),
]


class CircuitBreakerDetail(BaseModel):
    event_name: str
    impact_stars: int
    event_timestamp: str
    mins_to_event: float
    buffer_mins: int
    status: str  # "HALT_ACTIVE", "APPROACHING", "NORMAL"


class BreakingNewsAlert(BaseModel):
    headline: str
    urgency: str  # "CRITICAL", "HIGH", "MEDIUM"
    detected_at: str


class RecommendationForGovernor(BaseModel):
    action: str  # "HALT_NEW_ORDERS", "TIGHTEN_RISK", "NORMAL_OPERATION"
    reason: str
    suggested_risk_scale: float = Field(default=1.0, ge=0.0, le=1.0)


class MacroInsightReport(BaseModel):
    agent: str = "NEWS_AND_EVENT_AGENT"
    timestamp: str
    macro_sentiment_score: float  # -1.00 đến +1.00
    macro_bias: str  # "BULLISH_GOLD", "BEARISH_GOLD", "NEUTRAL"
    dxy_correlation_bias: str  # "BEARISH_DXY", "BULLISH_DXY", "NEUTRAL"
    active_circuit_breaker: bool
    circuit_breaker_details: Optional[CircuitBreakerDetail] = None
    breaking_news_alerts: list[BreakingNewsAlert] = []
    recommendation_for_governor: RecommendationForGovernor
    high_impact_events_upcoming: list[dict[str, Any]] = []
    macro_summary: str
    recommended_poll_interval_seconds: int = 300


class NewsEventAgent:
    """
    News & Event Agent (Phase 03 - Sprint 02):
    - Quản trị toàn diện việc thu thập tin tức và lịch kinh tế vĩ mô.
    - Phân tích tác động định lượng của các sự kiện 3 sao USD (Surprise Factor).
    - Đo lường cảm xúc vĩ mô (Macro Sentiment) đối với Vàng (XAUUSD) và Dollar Index (DXY).
    - Điều phối Macro News Circuit Breaker (+/- 30 phút quanh tin 3 sao USD).
    - Cung cấp Executive Recommendations cho Strategy Governor.
    """

    def __init__(self, default_buffer_mins: int = 30) -> None:
        self.default_buffer_mins = default_buffer_mins
        self._last_report: Optional[MacroInsightReport] = None

    async def generate_macro_report(
        self,
        session: AsyncSession,
        target_time: datetime | None = None,
        broadcast: bool = True,
    ) -> MacroInsightReport:
        """
        Tổng hợp báo cáo MacroInsightReport toàn diện từ dữ liệu lịch kinh tế và tin tức.
        """
        now = target_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Đọc cấu hình buffer từ SystemTradingConfig
        cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
        buffer_mins = cfg.news_circuit_breaker_buffer_mins if cfg else self.default_buffer_mins
        circuit_enabled = cfg.news_circuit_breaker_enabled if cfg else True

        # 2. Kiểm tra Circuit Breaker qua NewsCircuitBreaker
        is_circuit_active, halt_reason, cb_info = await news_circuit_breaker.is_circuit_active(
            session=session,
            target_time=now,
            buffer_mins=buffer_mins,
        )

        cb_detail: Optional[CircuitBreakerDetail] = None
        if is_circuit_active and cb_info:
            cb_detail = CircuitBreakerDetail(
                event_name=cb_info.get("title", "High-Impact Economic Event"),
                impact_stars=int(cb_info.get("impact_stars", 3)),
                event_timestamp=cb_info.get("event_timestamp", now.isoformat()),
                mins_to_event=float(cb_info.get("time_diff_minutes", 0.0)),
                buffer_mins=buffer_mins,
                status="HALT_ACTIVE",
            )

        # 3. Quét sự kiện 3 sao USD sắp tới trong 24 giờ
        upcoming_window_end = now + timedelta(hours=24)
        upcoming_query = (
            select(EconomicEvent)
            .where(
                EconomicEvent.impact_stars == 3,
                EconomicEvent.currency == "USD",
                EconomicEvent.event_timestamp.is_not(None),
                EconomicEvent.event_timestamp >= now,
                EconomicEvent.event_timestamp <= upcoming_window_end,
            )
            .order_by(EconomicEvent.event_timestamp.asc())
            .limit(5)
        )
        upcoming_events = (await session.scalars(upcoming_query)).all()
        upcoming_list: list[dict[str, Any]] = []
        for ev in upcoming_events:
            if ev.event_timestamp:
                diff_m = round((ev.event_timestamp - now).total_seconds() / 60.0, 1)
                upcoming_list.append({
                    "id": ev.id,
                    "title": ev.title,
                    "event_timestamp": ev.event_timestamp.isoformat(),
                    "mins_until": diff_m,
                    "forecast": ev.forecast_value,
                    "previous": ev.previous_value,
                })

        # 4. Tính toán Surprise Factor từ các sự kiện đã công bố trong 24h qua
        past_window_start = now - timedelta(hours=24)
        recent_events_query = (
            select(EconomicEvent)
            .where(
                EconomicEvent.currency == "USD",
                EconomicEvent.impact_stars >= 2,
                EconomicEvent.event_timestamp.is_not(None),
                EconomicEvent.event_timestamp >= past_window_start,
                EconomicEvent.event_timestamp <= now,
            )
            .order_by(EconomicEvent.event_timestamp.desc())
            .limit(10)
        )
        recent_events = (await session.scalars(recent_events_query)).all()
        event_impact_score = self._calculate_event_surprise_impact(recent_events)

        # 5. Phân tích tin tức gần đây (FinancialNews) và tính điểm cảm xúc có trọng số thời gian
        news_query = (
            select(FinancialNews)
            .where(
                FinancialNews.published_at.is_not(None),
                FinancialNews.published_at >= past_window_start,
                FinancialNews.published_at <= now,
            )
            .order_by(FinancialNews.published_at.desc())
            .limit(20)
        )
        recent_news = (await session.scalars(news_query)).all()

        news_sentiment_score = 0.0
        breaking_alerts: list[BreakingNewsAlert] = []

        if recent_news:
            weighted_scores: list[float] = []
            weights: list[float] = []
            for n in recent_news:
                score = float(n.sentiment_score) if n.sentiment_score is not None else 0.0
                hours_ago = max(0.1, (now - n.published_at).total_seconds() / 3600.0)
                # Trọng số suy giảm theo thời gian (decay factor sau 6 tiếng)
                w = math.exp(-hours_ago / 6.0)
                weighted_scores.append(score * w)
                weights.append(w)

                # Phát hiện Breaking News trong 2 giờ qua
                if hours_ago <= 2.0:
                    text_to_check = f"{n.title} {n.content or ''}"
                    for pat in _BREAKING_KEYWORDS:
                        if pat.search(text_to_check):
                            urgency = "CRITICAL" if (n.impact_stars or 1) >= 3 else "HIGH"
                            breaking_alerts.append(
                                BreakingNewsAlert(
                                    headline=n.title,
                                    urgency=urgency,
                                    detected_at=n.published_at.isoformat(),
                                )
                            )
                            break

            if weights and sum(weights) > 0:
                news_sentiment_score = sum(weighted_scores) / sum(weights)

        # 6. Tổng hợp Macro Sentiment Score (-1.00 đến +1.00)
        # Kết hợp 65% cảm xúc tin tức + 35% tác động số liệu kinh tế thực tế
        macro_score = (0.65 * news_sentiment_score) + (0.35 * event_impact_score)
        macro_score = max(-1.0, min(1.0, round(macro_score, 2)))

        # Xác định Bias
        if macro_score > 0.25:
            macro_bias = "BULLISH_GOLD"
            dxy_bias = "BEARISH_DXY"
        elif macro_score < -0.25:
            macro_bias = "BEARISH_GOLD"
            dxy_bias = "BULLISH_DXY"
        else:
            macro_bias = "NEUTRAL"
            dxy_bias = "NEUTRAL"

        # 7. Đề xuất hành động cho Strategy Governor
        if is_circuit_active:
            rec = RecommendationForGovernor(
                action="HALT_NEW_ORDERS",
                reason=f"High-impact US economic event active window (+/- {buffer_mins} mins): {cb_detail.event_name if cb_detail else '3-Star Event'}",
                suggested_risk_scale=0.0,
            )
        elif breaking_alerts and any(a.urgency == "CRITICAL" for a in breaking_alerts):
            rec = RecommendationForGovernor(
                action="TIGHTEN_RISK",
                reason=f"Critical breaking news detected: {breaking_alerts[0].headline}",
                suggested_risk_scale=0.5,
            )
        elif abs(macro_score) >= 0.50:
            rec = RecommendationForGovernor(
                action="NORMAL_OPERATION",
                reason=f"Strong macro sentiment ({macro_bias}) supporting trend continuation.",
                suggested_risk_scale=1.0,
            )
        else:
            rec = RecommendationForGovernor(
                action="NORMAL_OPERATION",
                reason="Macro environment normal, standard risk parameters permitted.",
                suggested_risk_scale=1.0,
            )

        # 8. Tóm tắt định tính
        summary_parts = [
            f"Tâm lý vĩ mô Vàng: {macro_bias} ({macro_score:+.2f}).",
            f"Tương quan USD/DXY: {dxy_bias}.",
        ]
        if is_circuit_active:
            summary_parts.append(f"CẢNH BÁO: Bộ ngắt mạch Circuit Breaker đang BẬT ({halt_reason}).")
        elif upcoming_list:
            next_ev = upcoming_list[0]
            summary_parts.append(f"Tin 3 sao kế tiếp: '{next_ev['title']}' trong {next_ev['mins_until']:.0f} phút nữa.")
        if breaking_alerts:
            summary_parts.append(f"Phát hiện {len(breaking_alerts)} tin breaking đáng chú ý.")

        macro_summary = " ".join(summary_parts)

        # 9. Đề xuất tần suất quét thích ứng (Adaptive Polling Interval)
        poll_interval = 300
        if upcoming_list and upcoming_list[0]["mins_until"] <= 60.0:
            poll_interval = 60
        elif is_circuit_active or breaking_alerts:
            poll_interval = 60

        report = MacroInsightReport(
            timestamp=now.isoformat(),
            macro_sentiment_score=macro_score,
            macro_bias=macro_bias,
            dxy_correlation_bias=dxy_bias,
            active_circuit_breaker=is_circuit_active,
            circuit_breaker_details=cb_detail,
            breaking_news_alerts=breaking_alerts,
            recommendation_for_governor=rec,
            high_impact_events_upcoming=upcoming_list,
            macro_summary=macro_summary,
            recommended_poll_interval_seconds=poll_interval,
        )

        self._last_report = report

        # 10. Phát sự kiện ra Redis Pub/Sub nếu cần
        if broadcast:
            await self._broadcast_macro_event(report)

        return report

    def _calculate_event_surprise_impact(self, events: list[EconomicEvent]) -> float:
        """
        Tính toán tác động của độ lệch Actual vs Forecast đối với Vàng:
        - Lạm phát (CPI, PPI) / Việc làm (NFP) tăng mạnh hơn kỳ vọng -> USD mạnh -> Vàng giảm (điểm âm).
        - Thất nghiệp (Jobless claims, Unemployment) tăng mạnh hơn kỳ vọng -> USD yếu -> Vàng tăng (điểm dương).
        """
        if not events:
            return 0.0

        scores: list[float] = []
        for ev in events:
            if not ev.actual_value or not ev.forecast_value:
                continue

            # Thử trích xuất giá trị số
            act_val = self._parse_numeric_str(ev.actual_value)
            fc_val = self._parse_numeric_str(ev.forecast_value)
            if act_val is None or fc_val is None or fc_val == 0:
                continue

            diff_pct = (act_val - fc_val) / abs(fc_val)
            title_lower = ev.title.lower()

            # Nhóm 1: Tăng trưởng, Lạm phát, NFP (Tốt cho USD -> Xấu cho Vàng)
            if any(k in title_lower for k in ("cpi", "ppi", "nfp", "non-farm", "payrolls", "gdp", "retail sales")):
                if diff_pct > 0.02:
                    scores.append(-0.35)  # USD beat -> Gold bearish
                elif diff_pct < -0.02:
                    scores.append(+0.35)  # USD miss -> Gold bullish

            # Nhóm 2: Thất nghiệp, Trợ cấp (Tốt cho Vàng -> Xấu cho USD)
            elif any(k in title_lower for k in ("unemployment", "jobless claims")):
                if diff_pct > 0.02:
                    scores.append(+0.30)  # Thất nghiệp tăng -> Gold bullish
                elif diff_pct < -0.02:
                    scores.append(-0.30)  # Thất nghiệp giảm -> Gold bearish

        return round(sum(scores) / len(scores), 2) if scores else 0.0

    @staticmethod
    def _parse_numeric_str(val_str: str) -> Optional[float]:
        clean = re.sub(r"[^\d.-]", "", val_str)
        try:
            return float(clean) if clean else None
        except ValueError:
            return None

    async def _broadcast_macro_event(self, report: MacroInsightReport) -> None:
        """Phát sóng sự kiện lên Redis Pub/Sub"""
        try:
            payload = report.model_dump_json()
            await redis_client.publish(REDIS_CHANNEL_NEWS_AGENT, payload)
        except Exception as exc:
            logger.debug("Failed to publish macro report to Redis: %s", exc)

    async def trigger_scan(self) -> dict[str, Any]:
        """
        Kích hoạt thủ công chu trình quét tin tức và lịch kinh tế tức thời (News Collector Controller).
        """
        calendar_events_count = 0
        news_items_count = 0
        errors: list[str] = []

        timeout = httpx.Timeout(connect=3.0, read=8.0, write=8.0, pool=3.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            # 1. Quét lịch kinh tế FairEconomy
            try:
                cal_resp = await http.get(settings.fair_economy_calendar_url)
                if cal_resp.status_code == 200:
                    events = parse_fair_economy_calendar(cal_resp.json())
                    calendar_events_count = len(events)
            except Exception as exc:
                errors.append(f"FairEconomy calendar scan failed: {exc}")

            # 2. Quét RSS Kitco
            try:
                kitco_resp = await http.get(settings.kitco_news_rss_url)
                if kitco_resp.status_code == 200:
                    news_kitco = parse_rss_feed(kitco_resp.content, "Kitco News", gold_only=True)
                    news_items_count += len(news_kitco)
            except Exception as exc:
                errors.append(f"Kitco RSS scan failed: {exc}")

            # 3. Quét RSS FXStreet
            try:
                fxs_resp = await http.get(settings.fxstreet_news_rss_url)
                if fxs_resp.status_code == 200:
                    news_fxs = parse_rss_feed(fxs_resp.content, "FXStreet News", gold_only=True)
                    news_items_count += len(news_fxs)
            except Exception as exc:
                errors.append(f"FXStreet RSS scan failed: {exc}")

        return {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "calendar_events_detected": calendar_events_count,
            "news_items_detected": news_items_count,
            "errors": errors,
            "status": "COMPLETED" if not errors else "PARTIAL_SUCCESS",
        }

    async def get_circuit_breaker_status(
        self, session: AsyncSession, target_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        Lấy chi tiết trạng thái Circuit Breaker hiện tại và lịch sự kiện tiếp theo.
        """
        now = target_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        cfg = await session.scalar(select(SystemTradingConfig).where(SystemTradingConfig.id == 1))
        buffer_mins = cfg.news_circuit_breaker_buffer_mins if cfg else self.default_buffer_mins
        is_enabled = cfg.news_circuit_breaker_enabled if cfg else True

        is_active, reason, info = await news_circuit_breaker.is_circuit_active(
            session=session,
            target_time=now,
            buffer_mins=buffer_mins,
        )

        return {
            "timestamp": now.isoformat(),
            "circuit_breaker_enabled": is_enabled,
            "is_active": is_active,
            "halt_reason": reason,
            "buffer_mins": buffer_mins,
            "active_event_info": info,
        }


news_event_agent = NewsEventAgent()
