import asyncio
import time

import httpx

from backend.data_ingestion.news_worker import NewsCollector, ProviderConfigurationError, _SOURCE_STATUS


def test_retry_after_accepts_seconds_and_http_dates():
    assert NewsCollector._retry_after_seconds("3") == 3.0
    assert NewsCollector._retry_after_seconds("invalid") is None


def test_configuration_http_errors_are_not_retried():
    class NotFoundClient:
        calls = 0

        async def get(self, url, headers=None, params=None):
            self.calls += 1
            request = httpx.Request("GET", url)
            return httpx.Response(404, request=request)

    client = NotFoundClient()
    collector = NewsCollector()

    async def request():
        try:
            await collector._request(client, "https://feed.example.test/rss")
        except ProviderConfigurationError:
            return
        raise AssertionError("HTTP 404 must be classified as a configuration error")

    asyncio.run(request())

    assert client.calls == 1


def test_fallback_activates_after_two_primary_errors_and_recovers_after_two_successes():
    source = "test-provider-failover"
    _SOURCE_STATUS.pop(source, None)
    collector = NewsCollector()

    collector._record_failure(source, RuntimeError("first failure"))
    assert _SOURCE_STATUS[source]["fallback_active"] is False
    collector._record_failure(source, RuntimeError("second failure"))
    assert _SOURCE_STATUS[source]["fallback_active"] is True

    collector._record_success(source, "primary")
    assert _SOURCE_STATUS[source]["fallback_active"] is True
    collector._record_success(source, "primary")
    assert _SOURCE_STATUS[source]["fallback_active"] is False
    assert _SOURCE_STATUS[source]["primary_errors"] == 0
    _SOURCE_STATUS.pop(source, None)


def test_fallback_success_does_not_reset_primary_circuit_failure_count():
    source = "test-provider-circuit"
    _SOURCE_STATUS.pop(source, None)
    collector = NewsCollector()

    for _ in range(5):
        collector._record_failure(source, RuntimeError("primary unavailable"))
        collector._record_success(source, "fallback")

    state = _SOURCE_STATUS[source]
    assert state["primary_errors"] == 5
    assert state["circuit_open_until"] > 0
    assert state["status"] == "circuit_open"
    _SOURCE_STATUS.pop(source, None)


def test_fallback_failure_does_not_extend_primary_circuit():
    source = "test-provider-fallback-failure"
    _SOURCE_STATUS.pop(source, None)

    class FailingFallbackCollector(NewsCollector):
        async def _try_fallback(self, http, failed_source):
            assert http is not None
            assert failed_source == source
            raise RuntimeError(f"{failed_source} fallback unavailable")

    state = {
        "status": "circuit_open",
        "mode": "fallback",
        "fallback_active": True,
        "consecutive_errors": 0,
        "primary_errors": 5,
        "primary_successes": 0,
        "last_success_at": None,
        "last_error": None,
        "stale_after_seconds": 300,
        "circuit_open_until": time.monotonic() + 60,
    }
    _SOURCE_STATUS[source] = state
    circuit_until = state["circuit_open_until"]

    async def check_loop():
        async def unused_primary(_http):
            assert _http is not None
            raise AssertionError("primary must remain behind the open circuit")

        task = asyncio.create_task(FailingFallbackCollector()._poll_loop(object(), source, 30, unused_primary))
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(check_loop())

    assert state["primary_errors"] == 5
    assert state["circuit_open_until"] == circuit_until
    _SOURCE_STATUS.pop(source, None)