from datetime import datetime, timezone

from backend.data_ingestion.news_sources import (
    classify_impact,
    parse_fair_economy_calendar,
    parse_finnhub_economic_calendar,
    parse_finnhub_market_news,
    parse_rss_feed,
)


def test_event_classifier_uses_event_types_and_unknown_fallback():
    assert classify_impact("US CPI y/y")[:2] == (3, "CLASSIFIED")
    assert classify_impact("US Retail Sales m/m")[:2] == (2, "CLASSIFIED")
    assert classify_impact("ADP Non-Farm Employment Change")[:2] == (2, "CLASSIFIED")
    assert classify_impact("Treasury auction", provider_impact="Low")[:2] == (1, "CLASSIFIED")
    assert classify_impact("Unmapped event")[:2] == (None, "UNKNOWN")


def test_fair_economy_calendar_normalizes_offset_to_utc():
    events = parse_fair_economy_calendar(
        [
            {
                "title": "Non-Farm Employment Change",
                "country": "USD",
                "date": "2026-10-02T08:30:00-04:00",
                "impact": "High",
                "forecast": "89K",
                "previous": "162K",
            }
        ]
    )

    assert len(events) == 1
    assert events[0]["event_timestamp"] == datetime(2026, 10, 2, 12, 30, tzinfo=timezone.utc)
    assert events[0]["timezone_status"] == "VERIFIED"
    assert events[0]["impact_stars"] == 3


def test_calendar_keeps_same_title_events_on_same_day_distinct():
    duplicate = {
        "title": "USD holiday schedule",
        "country": "USD",
        "date": "2026-10-02T08:00:00-04:00",
        "impact": "Low",
    }
    events = parse_fair_economy_calendar([duplicate, {**duplicate, "date": "2026-10-02T09:00:00-04:00"}])

    assert len(events) == 2
    assert events[0]["dedupe_key"] != events[1]["dedupe_key"]


def test_finnhub_calendar_keeps_unverified_time_without_countdown_timestamp():
    events = parse_finnhub_economic_calendar(
        {
            "economicCalendar": [
                {
                    "event": "Retail Sales",
                    "country": "US",
                    "time": "2026-10-02 08:30:00",
                    "impact": "medium",
                    "estimate": "0.2%",
                }
            ]
        }
    )

    assert events[0]["event_timestamp"] is None
    assert events[0]["provider_time_raw"] == "2026-10-02 08:30:00"
    assert events[0]["timezone_status"] == "UNKNOWN"
    assert events[0]["impact_stars"] == 2


def test_rss_parser_uses_guid_and_published_timestamp():
    feed = b"""<?xml version='1.0'?>
    <rss version='2.0'><channel><title>Kitco News</title><item>
      <title>Gold price reacts to CPI</title>
      <guid isPermaLink='false'>kitco-item-1</guid>
      <link>https://example.test/gold-cpi</link>
      <pubDate>Wed, 30 Sep 2026 17:51:01 EDT</pubDate>
      <description>Gold market update.</description>
    </item></channel></rss>"""

    items = parse_rss_feed(feed, "Kitco News", gold_only=True)

    assert len(items) == 1
    assert items[0]["external_id"] == "kitco-item-1"
    assert items[0]["published_at"] == "2026-09-30T21:51:01+00:00"
    assert items[0]["dedupe_key"] is None


def test_general_rss_can_filter_to_xau_usd_relevance():
        feed = b"""<?xml version='1.0'?>
        <rss version='2.0'><channel><item><title>Local sports result</title>
            <guid>sports-1</guid><pubDate>Wed, 30 Sep 2026 17:51:01 GMT</pubDate>
        </item><item><title>Gold rises as USD retreats</title><guid>gold-1</guid>
            <pubDate>Wed, 30 Sep 2026 17:52:01 GMT</pubDate></item></channel></rss>"""

        items = parse_rss_feed(feed, "FXStreet News", gold_only=True)

        assert [item["external_id"] for item in items] == ["gold-1"]


def test_rss_item_without_guid_or_link_gets_canonical_dedupe_key():
        feed = b"""<?xml version='1.0'?>
        <rss version='2.0'><channel><item>
            <title>Gold and USD market update</title>
            <pubDate>Wed, 30 Sep 2026 17:51:01 GMT</pubDate>
        </item></channel></rss>"""

        item = parse_rss_feed(feed, "Fallback RSS", gold_only=True)[0]

        assert item["external_id"] is None
        assert len(item["dedupe_key"]) == 64


def test_finnhub_market_news_filters_relevance_and_uses_provider_id():
    items = parse_finnhub_market_news(
        [
            {
                "id": 123,
                "datetime": 1790942400,
                "headline": "Gold holds as Treasury yields rise",
                "summary": "The dollar also moved higher.",
                "url": "https://example.test/story",
            },
            {"id": 124, "datetime": 1790942400, "headline": "Local sports result", "summary": "No market terms."},
        ]
    )

    assert len(items) == 1
    assert items[0]["external_id"] == "123"
    assert items[0]["source"] == "Finnhub Market News"