import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy import select

from core.config import settings
from core.database import session_factory
from core.models import EconomicEvent, EconomicEventRevision, FinancialNews
from core.redis_client import client as redis_client
from data_ingestion.news_sources import (
    _content_hash,
    parse_fair_economy_calendar,
    parse_finnhub_economic_calendar,
    parse_finnhub_market_news,
    parse_rss_feed,
)

logger = logging.getLogger(__name__)


class ProviderConfigurationError(RuntimeError):
    pass


_SOURCE_STATUS: dict[str, dict[str, object]] = {}
_POLL_SECONDS = {
    "FairEconomy": 300,
    "Kitco News": 120,
    "FXStreet News": 120,
}


def get_source_status() -> dict[str, dict[str, object]]:
    now = datetime.now(timezone.utc)
    result: dict[str, dict[str, object]] = {}
    for name, state in _SOURCE_STATUS.items():
        copy = dict(state)
        last_success = copy.get("last_success_at")
        stale_after = int(copy.get("stale_after_seconds", 0))
        stale = isinstance(last_success, datetime) and (now - last_success).total_seconds() > stale_after
        copy["stale"] = stale
        copy["last_success_at"] = last_success.isoformat() if isinstance(last_success, datetime) else None
        result[name] = copy
    return result


def _new_state(stale_after_seconds: int) -> dict[str, object]:
    return {
        "status": "starting",
        "mode": "primary",
        "fallback_active": False,
        "primary_disabled": False,
        "fallback_disabled": False,
        "consecutive_errors": 0,
        "primary_errors": 0,
        "primary_successes": 0,
        "last_success_at": None,
        "last_error": None,
        "stale_after_seconds": stale_after_seconds,
        "circuit_open_until": 0.0,
    }


class NewsCollector:
    def __init__(self) -> None:
        self._validators: dict[str, dict[str, str]] = {}
        self._finnhub_min_ids = {"forex": 0, "general": 0}
        self._finnhub_cursor_loaded: set[str] = set()

    async def run(self) -> None:
        timeout = httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            await asyncio.gather(
                self._poll_loop(http, "FairEconomy", 300, self._poll_calendar),
                self._poll_loop(http, "Kitco News", 120, self._poll_kitco),
                self._poll_loop(http, "FXStreet News", 120, self._poll_fxstreet),
            )

    async def _poll_loop(
        self,
        http: httpx.AsyncClient,
        source: str,
        interval: int,
        poll: Callable[[httpx.AsyncClient], Awaitable[None]],
    ) -> None:
        _SOURCE_STATUS.setdefault(source, _new_state(interval * 3))
        while True:
            try:
                state = _SOURCE_STATUS[source]
                now = time.monotonic()
                circuit_until = float(state["circuit_open_until"])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("News worker state error for %s: %s", source, exc)
                await asyncio.sleep(interval)
                continue

            if not state["primary_disabled"] and now >= circuit_until:
                if circuit_until:
                    state["circuit_open_until"] = 0.0
                    state["status"] = "probing"
                try:
                    await poll(http)
                except asyncio.CancelledError:
                    raise
                except Exception as primary_error:
                    self._record_failure(source, primary_error)
                    logger.warning("Primary news poll failed for %s: %s", source, primary_error)
                    if isinstance(primary_error, ProviderConfigurationError):
                        state["primary_disabled"] = True
                        state["fallback_active"] = True

            if state["fallback_active"] and not state["fallback_disabled"]:
                try:
                    await self._try_fallback(http, source)
                except asyncio.CancelledError:
                    raise
                except Exception as fallback_error:
                    state["status"] = "fallback_error"
                    state["last_error"] = str(fallback_error)[:300]
                    if isinstance(fallback_error, ProviderConfigurationError):
                        state["fallback_disabled"] = True
                        state["status"] = "fallback_unavailable"
                    logger.warning("News fallback failed for %s: %s", source, fallback_error)
            await asyncio.sleep(interval)

    async def _request(
        self,
        http: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        for attempt, base_delay in enumerate((1.0, 2.0, 4.0)):
            try:
                response = await http.get(url, headers=headers, params=params)
                if response.status_code == 429:
                    retry_after = self._retry_after_seconds(response.headers.get("Retry-After"))
                    if attempt < 2:
                        await asyncio.sleep(retry_after if retry_after is not None else base_delay)
                        continue
                if response.status_code in {408} or response.status_code >= 500:
                    if attempt < 2:
                        await asyncio.sleep(base_delay * random.uniform(0.8, 1.2))
                        continue
                if response.status_code == 304:
                    return response
                if response.status_code in {401, 403, 404}:
                    raise ProviderConfigurationError(
                        f"Provider returned non-retryable HTTP {response.status_code} for {url}"
                    )
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise
                await asyncio.sleep(base_delay * random.uniform(0.8, 1.2))
        raise RuntimeError("Provider request exhausted retries")

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                target = parsedate_to_datetime(value)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    def _record_success(self, source: str, mode: str) -> None:
        state = _SOURCE_STATUS.setdefault(source, _new_state(_POLL_SECONDS.get(source, 120) * 3))
        state["last_success_at"] = datetime.now(timezone.utc)
        if mode == "primary":
            state["consecutive_errors"] = 0
            state["primary_errors"] = 0
            state["last_error"] = None
            successes = int(state["primary_successes"]) + 1
            state["primary_successes"] = successes
            if successes >= 2:
                state["fallback_active"] = False
                state["mode"] = "primary"
        else:
            state["consecutive_errors"] = 0
            state["fallback_active"] = True
            state["mode"] = "fallback"
        if float(state["circuit_open_until"]) > time.monotonic():
            state["status"] = "circuit_open"
        else:
            state["status"] = "healthy" if not state["fallback_active"] else "degraded"

    def _record_failure(self, source: str, error: Exception) -> None:
        state = _SOURCE_STATUS.setdefault(source, _new_state(_POLL_SECONDS.get(source, 120) * 3))
        failures = int(state["consecutive_errors"]) + 1
        state["consecutive_errors"] = failures
        primary_failures = int(state["primary_errors"]) + 1
        state["primary_errors"] = primary_failures
        state["primary_successes"] = 0
        state["last_error"] = str(error)[:300]
        state["status"] = "degraded" if state.get("last_success_at") else "unavailable"
        if failures >= 2:
            state["fallback_active"] = True
        if primary_failures >= 5:
            state["circuit_open_until"] = time.monotonic() + 300
            state["status"] = "circuit_open"

    async def _poll_calendar(self, http: httpx.AsyncClient) -> None:
        source = "FairEconomy"
        response = await self._request(http, settings.fair_economy_calendar_url)
        events = parse_fair_economy_calendar(response.json())
        changed = await self._upsert_events(events)
        self._record_success(source, "primary")
        await self._publish_updates("economic_event", changed)

    async def _poll_kitco(self, http: httpx.AsyncClient) -> None:
        await self._poll_rss(http, "Kitco News", settings.kitco_news_rss_url, gold_only=True)

    async def _poll_fxstreet(self, http: httpx.AsyncClient) -> None:
        await self._poll_rss(http, "FXStreet News", settings.fxstreet_news_rss_url, gold_only=True)

    async def _poll_rss(
        self, http: httpx.AsyncClient, source: str, url: str, gold_only: bool = False
    ) -> None:
        headers = {"Accept": "application/rss+xml, application/xml"}
        headers.update(self._validators.get(url, {}))
        response = await self._request(http, url, headers=headers)
        if response.status_code == 304:
            self._record_success(source, "primary")
            return
        validators = {}
        if response.headers.get("ETag"):
            validators["If-None-Match"] = response.headers["ETag"]
        if response.headers.get("Last-Modified"):
            validators["If-Modified-Since"] = response.headers["Last-Modified"]
        self._validators[url] = validators
        news = parse_rss_feed(response.content, source, gold_only=gold_only)
        changed = await self._upsert_news(news)
        self._record_success(source, "primary")
        await self._publish_updates("breaking_news", changed)

    async def _try_fallback(self, http: httpx.AsyncClient, source: str) -> None:
        state = _SOURCE_STATUS.get(source)
        if not state or not state["fallback_active"]:
            return
        if not settings.finnhub_api_key:
            state["status"] = "fallback_unavailable"
            state["last_error"] = "Finnhub API key is not configured"
            state["fallback_disabled"] = True
            return
        if source == "FairEconomy":
            if not settings.finnhub_economic_calendar_enabled:
                state["status"] = "fallback_unavailable"
                state["last_error"] = "Finnhub Economic Calendar requires enabled Premium entitlement"
                state["fallback_disabled"] = True
                return
            await self._poll_finnhub_calendar(http, source)
            return
        category = "general" if source == "Kitco News" else "forex"
        await self._poll_finnhub_news(http, source, category)

    async def _poll_finnhub_calendar(self, http: httpx.AsyncClient, primary_source: str) -> None:
        now = datetime.now(timezone.utc).date()
        response = await self._request(
            http,
            "https://finnhub.io/api/v1/calendar/economic",
            headers={"X-Finnhub-Token": settings.finnhub_api_key or ""},
            params={"from": now.isoformat(), "to": (now + timedelta(days=7)).isoformat()},
        )
        events = parse_finnhub_economic_calendar(response.json())
        changed = await self._upsert_events(events)
        self._record_success(primary_source, "fallback")
        await self._publish_updates("economic_event", changed)

    async def _poll_finnhub_news(
        self, http: httpx.AsyncClient, primary_source: str, category: str
    ) -> None:
        cursor_key = f"news:finnhub:min_id:{category}"
        if category not in self._finnhub_cursor_loaded:
            stored_cursor = await redis_client.get(cursor_key)
            if stored_cursor and stored_cursor.isdigit():
                self._finnhub_min_ids[category] = int(stored_cursor)
            self._finnhub_cursor_loaded.add(category)
        response = await self._request(
            http,
            "https://finnhub.io/api/v1/news",
            headers={"X-Finnhub-Token": settings.finnhub_api_key or ""},
            params={"category": category, "minId": self._finnhub_min_ids[category]},
        )
        payload = response.json()
        if isinstance(payload, list):
            ids = [int(item["id"]) for item in payload if isinstance(item, dict) and str(item.get("id", "")).isdigit()]
            if ids:
                self._finnhub_min_ids[category] = max(0, max(ids) - 100)
                await redis_client.set(cursor_key, self._finnhub_min_ids[category])
        news = parse_finnhub_market_news(payload)
        changed = await self._upsert_news(news)
        self._record_success(primary_source, "fallback")
        await self._publish_updates("breaking_news", changed)

    async def _upsert_news(self, items: list[dict[str, Any]]) -> list[dict[str, object]]:
        changed: list[dict[str, object]] = []
        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            for item in items:
                source = str(item["source"])
                external_id = item.get("external_id")
                dedupe_key = item.get("dedupe_key")
                identity_filter = (
                    FinancialNews.external_id == external_id
                    if external_id
                    else FinancialNews.dedupe_key == dedupe_key
                )
                row = await session.scalar(
                    select(FinancialNews).where(FinancialNews.source == source, identity_filter).limit(1)
                )
                published_at = self._parse_datetime(item.get("published_at")) or now
                fields = {
                    "title": str(item["title"]),
                    "content": str(item.get("content") or ""),
                    "published_at": published_at.isoformat(),
                    "source_url": str(item.get("url") or "") or None,
                    "impact_stars": item.get("impact_stars"),
                    "classification_status": str(item.get("classification_status", "UNKNOWN")),
                }
                item_hash = str(item.get("content_hash") or _content_hash(fields))
                if row is None:
                    stars = fields["impact_stars"]
                    row = FinancialNews(
                        source=source,
                        title=fields["title"],
                        content=fields["content"] or None,
                        published_at=published_at,
                        source_url=fields["source_url"],
                        external_id=external_id,
                        dedupe_key=dedupe_key,
                        content_hash=item_hash,
                        revision_no=1,
                        last_seen_at=now,
                        impact_stars=stars,
                        classification_status=fields["classification_status"],
                        keywords_matched=item.get("keywords_matched"),
                        impact_level={1: "LOW", 2: "MEDIUM", 3: "HIGH"}.get(stars, "UNKNOWN"),
                    )
                    session.add(row)
                    await session.flush()
                    changed.append(self._news_event(row))
                    continue

                row.last_seen_at = now
                if row.content_hash == item_hash:
                    continue
                row.title = fields["title"]
                row.content = fields["content"] or None
                row.published_at = published_at
                row.source_url = fields["source_url"]
                row.content_hash = item_hash
                row.revision_no += 1
                row.impact_stars = fields["impact_stars"]
                row.classification_status = fields["classification_status"]
                row.keywords_matched = item.get("keywords_matched")
                row.impact_level = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}.get(row.impact_stars, "UNKNOWN")
                changed.append(self._news_event(row))
            await session.commit()
        return changed

    async def _upsert_events(self, items: list[dict[str, object]]) -> list[dict[str, object]]:
        changed: list[dict[str, object]] = []
        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            for item in items:
                source = str(item["source"])
                external_id = item.get("external_id")
                dedupe_key = item.get("dedupe_key")
                identity_filter = (
                    EconomicEvent.external_id == external_id
                    if external_id
                    else EconomicEvent.dedupe_key == dedupe_key
                )
                row = await session.scalar(
                    select(EconomicEvent).where(EconomicEvent.source == source, identity_filter).limit(1)
                )
                fields = self._event_fields(item)
                item_hash = _content_hash(fields)
                if row is None:
                    row = EconomicEvent(
                        source=source,
                        external_id=external_id,
                        dedupe_key=dedupe_key,
                        **fields,
                        content_hash=item_hash,
                        revision_no=1,
                        last_seen_at=now,
                    )
                    session.add(row)
                    await session.flush()
                    changed.append(self._economic_event_event(row))
                    continue

                row.last_seen_at = now
                if row.content_hash == item_hash:
                    continue
                session.add(
                    EconomicEventRevision(
                        economic_event_id=row.id,
                        revision_no=row.revision_no,
                        snapshot=self._event_snapshot(row),
                    )
                )
                for name, value in fields.items():
                    setattr(row, name, value)
                row.content_hash = item_hash
                row.revision_no += 1
                row.updated_at = now
                changed.append(self._economic_event_event(row))
            await session.commit()
        return changed

    @staticmethod
    def _event_fields(item: dict[str, object]) -> dict[str, object]:
        return {
            "title": str(item["title"]),
            "description": item.get("description"),
            "provider_time_raw": str(item["provider_time_raw"]),
            "event_timestamp": item.get("event_timestamp"),
            "timezone_status": str(item["timezone_status"]),
            "currency": str(item.get("currency") or "USD"),
            "previous_value": item.get("previous_value"),
            "forecast_value": item.get("forecast_value"),
            "actual_value": item.get("actual_value"),
            "impact_stars": item.get("impact_stars"),
            "classification_status": str(item.get("classification_status", "UNKNOWN")),
            "keywords_matched": item.get("keywords_matched"),
        }

    @staticmethod
    def _event_snapshot(row: EconomicEvent) -> dict[str, object]:
        return {
            "source": row.source,
            "external_id": row.external_id,
            "dedupe_key": row.dedupe_key,
            "title": row.title,
            "provider_time_raw": row.provider_time_raw,
            "event_timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
            "timezone_status": row.timezone_status,
            "currency": row.currency,
            "previous_value": row.previous_value,
            "forecast_value": row.forecast_value,
            "actual_value": row.actual_value,
            "impact_stars": row.impact_stars,
            "classification_status": row.classification_status,
            "content_hash": row.content_hash,
            "revision_no": row.revision_no,
        }

    @staticmethod
    def _news_event(row: FinancialNews) -> dict[str, object]:
        return {
            "id": row.id,
            "source": row.source,
            "title": row.title,
            "content": row.content,
            "published_at": row.published_at.isoformat(),
            "source_url": row.source_url,
            "impact_stars": row.impact_stars,
            "classification_status": row.classification_status,
            "impact_level": row.impact_level,
            "sentiment_score": float(row.sentiment_score) if row.sentiment_score is not None else None,
            "revision_no": row.revision_no,
        }

    @staticmethod
    def _economic_event_event(row: EconomicEvent) -> dict[str, object]:
        return {
            "id": row.id,
            "source": row.source,
            "title": row.title,
            "description": row.description,
            "provider_time_raw": row.provider_time_raw,
            "event_timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
            "timezone_status": row.timezone_status,
            "currency": row.currency,
            "previous_value": row.previous_value,
            "forecast_value": row.forecast_value,
            "actual_value": row.actual_value,
            "impact_stars": row.impact_stars,
            "classification_status": row.classification_status,
            "revision_no": row.revision_no,
        }

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None

    @staticmethod
    async def _publish_updates(kind: str, items: list[dict[str, object]]) -> None:
        channel = "news:events"
        for item in items:
            try:
                await redis_client.publish(
                    channel,
                    json.dumps(
                        {"type": "news.upsert", "kind": kind, "data": item},
                        separators=(",", ":"),
                    ),
                )
            except Exception as exc:
                logger.warning("Could not publish news update: %s", exc)