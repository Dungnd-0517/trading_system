import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

_RELEVANCE_TERMS = (
    "gold",
    "xau",
    "bullion",
    "precious metal",
    "usd",
    "federal reserve",
    "fed",
    "cpi",
    "ppi",
    "pce",
    "nfp",
    "nonfarm",
    "payroll",
    "inflation",
    "interest rate",
    "treasury yield",
    "fomc",
)
_HIGH_IMPACT = re.compile(r"\b(cpi|ppi|pce|nfp|nonfarm|fomc|rate decision|powell|war|invasion)\b", re.I)
_MEDIUM_IMPACT = re.compile(
    r"\b(pmi|retail sales|adp|consumer confidence|consumer sentiment|jobless claims|jolts)\b",
    re.I,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _matched_keywords(text: str) -> list[str]:
    folded = text.casefold()
    return [term for term in _RELEVANCE_TERMS if term in folded]


def classify_impact(title: str, description: str = "", provider_impact: str | None = None) -> tuple[int | None, str, list[str]]:
    text = f"{title} {description}"
    matched = _matched_keywords(text)
    if re.search(r"\bADP\b", text, re.I):
        return 2, "CLASSIFIED", matched
    if _HIGH_IMPACT.search(text):
        return 3, "CLASSIFIED", matched
    if _MEDIUM_IMPACT.search(text):
        return 2, "CLASSIFIED", matched
    impact = (provider_impact or "").strip().casefold()
    if impact in {"high", "3", "red"}:
        return 3, "CLASSIFIED", matched
    if impact in {"medium", "moderate", "2", "orange"}:
        return 2, "CLASSIFIED", matched
    if impact in {"low", "1", "yellow"}:
        return 1, "CLASSIFIED", matched
    return None, "UNKNOWN", matched


def _content_hash(fields: dict[str, object]) -> str:
    canonical = json.dumps(fields, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_fair_economy_calendar(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        raise ValueError("FairEconomy calendar payload must be an array")

    events: list[dict[str, object]] = []
    occurrences: dict[tuple[str, str, str], int] = {}
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        title = _clean(raw.get("title"))
        country = _clean(raw.get("country")).upper()
        provider_time_raw = _clean(raw.get("date"))
        if not title or (country != "USD" and not _matched_keywords(title)):
            continue

        parsed_time: datetime | None = None
        timezone_status = "UNKNOWN"
        try:
            candidate = datetime.fromisoformat(provider_time_raw.replace("Z", "+00:00"))
            if candidate.tzinfo is not None:
                parsed_time = candidate.astimezone(timezone.utc)
                timezone_status = "VERIFIED"
        except ValueError:
            pass

        impact_stars, classification_status, keywords = classify_impact(
            title, provider_impact=_clean(raw.get("impact"))
        )
        occurrence_key = (country, title.casefold(), provider_time_raw[:10])
        occurrence = occurrences.get(occurrence_key, 0)
        occurrences[occurrence_key] = occurrence + 1
        canonical = {
            "source": "FairEconomy",
            "currency": country,
            "title": title.casefold(),
            "event_date": provider_time_raw[:10],
            "occurrence": occurrence,
        }
        events.append(
            {
                "source": "FairEconomy",
                "external_id": None,
                "dedupe_key": _content_hash(canonical),
                "title": title,
                "description": None,
                "provider_time_raw": provider_time_raw,
                "event_timestamp": parsed_time,
                "timezone_status": timezone_status,
                "currency": country or "USD",
                "previous_value": _clean(raw.get("previous")) or None,
                "forecast_value": _clean(raw.get("forecast")) or None,
                "actual_value": _clean(raw.get("actual")) or None,
                "impact_stars": impact_stars,
                "classification_status": classification_status,
                "keywords_matched": keywords,
            }
        )
    return events


def parse_finnhub_economic_calendar(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("economicCalendar"), list):
        raise ValueError("Finnhub economic calendar payload has no economicCalendar array")

    events: list[dict[str, object]] = []
    occurrences: dict[tuple[str, str, str], int] = {}
    for raw in payload["economicCalendar"]:
        if not isinstance(raw, dict):
            continue
        title = _clean(raw.get("event"))
        country = _clean(raw.get("country")).upper()
        provider_time_raw = _clean(raw.get("time"))
        if not title or (country not in {"US", "USA", "USD"} and not _matched_keywords(title)):
            continue
        impact_stars, classification_status, keywords = classify_impact(
            title, provider_impact=_clean(raw.get("impact"))
        )
        occurrence_key = (country, title.casefold(), provider_time_raw[:10])
        occurrence = occurrences.get(occurrence_key, 0)
        occurrences[occurrence_key] = occurrence + 1
        canonical = {
            "source": "Finnhub Economic Calendar",
            "currency": country,
            "title": title.casefold(),
            "event_date": provider_time_raw[:10],
            "occurrence": occurrence,
        }
        events.append(
            {
                "source": "Finnhub Economic Calendar",
                "external_id": None,
                "dedupe_key": _content_hash(canonical),
                "title": title,
                "description": None,
                "provider_time_raw": provider_time_raw,
                "event_timestamp": None,
                "timezone_status": "UNKNOWN",
                "currency": country or "USD",
                "previous_value": _clean(raw.get("prev")) or None,
                "forecast_value": _clean(raw.get("estimate")) or None,
                "actual_value": _clean(raw.get("actual")) or None,
                "impact_stars": impact_stars,
                "classification_status": classification_status,
                "keywords_matched": keywords,
            }
        )
    return events


def parse_finnhub_market_news(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Finnhub market news payload must be an array")

    items: list[dict[str, Any]] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        title = _clean(raw.get("headline"))
        description = _clean(raw.get("summary"))
        keywords = _matched_keywords(f"{title} {description}")
        if not title or not keywords:
            continue
        try:
            published_at = datetime.fromtimestamp(int(raw["datetime"]), timezone.utc)
        except (KeyError, TypeError, ValueError, OSError):
            continue
        impact_stars, classification_status, matched = classify_impact(title, description)
        external_id = _clean(raw.get("id"))
        url = _clean(raw.get("url"))
        normalized = {
            "source": "Finnhub Market News",
            "title": title,
            "content": description,
            "published_at": published_at.isoformat(),
            "url": url,
            "impact_stars": impact_stars,
            "classification_status": classification_status,
        }
        items.append(
            {
                **normalized,
                "external_id": external_id or None,
                "dedupe_key": None if external_id else _content_hash(normalized),
                "content_hash": _content_hash(normalized),
                "keywords_matched": matched,
            }
        )
    return items


def parse_rss_feed(payload: bytes, source: str, gold_only: bool = False) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid RSS feed from {source}: {exc}") from exc
    channel = root.find("./channel")
    if root.tag != "rss" or channel is None:
        raise ValueError(f"Unsupported RSS structure from {source}")

    items: list[dict[str, Any]] = []
    for entry in channel.findall("./item"):
        title = _clean(entry.findtext("title"))
        description = _clean(entry.findtext("description"))
        combined = f"{title} {description}"
        keywords = _matched_keywords(combined)
        if not title or (gold_only and not keywords):
            continue

        published_raw = _clean(entry.findtext("pubDate"))
        published_at: datetime | None = None
        if published_raw:
            try:
                candidate = parsedate_to_datetime(published_raw)
                if candidate.tzinfo is not None:
                    published_at = candidate.astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass
        if published_at is None:
            published_at = datetime.now(timezone.utc)

        external_id = _clean(entry.findtext("guid")) or None
        url = _clean(entry.findtext("link")) or external_id or ""
        identity = external_id or url
        impact_stars, classification_status, matched = classify_impact(title, description)
        normalized = {
            "source": source,
            "title": title,
            "content": description,
            "published_at": published_at.isoformat(),
            "url": url,
            "impact_stars": impact_stars,
            "classification_status": classification_status,
        }
        items.append(
            {
                **normalized,
                "external_id": identity or None,
                "dedupe_key": None if identity else _content_hash(
                    {
                        "source": source,
                        "title": title.casefold(),
                        "published_at": published_at.isoformat(),
                    }
                ),
                "content_hash": _content_hash(normalized),
                "keywords_matched": matched,
            }
        )
    return items