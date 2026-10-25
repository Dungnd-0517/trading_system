import asyncio
import json
import pytest
from fastapi import WebSocketDisconnect
from redis.asyncio import Redis

from ai_engine.council_aggregator import (
    AgentCouncilState,
    council_aggregator,
    REDIS_CHANNEL_AGENT_STATE,
    REDIS_KEY_COUNCIL_CACHE,
)
from api.v1.websocket import _AGENT_CHANNELS, _CHANNELS, agents_stream, market_stream
from core.config import settings
from core.database import session_factory


def test_websocket_channel_configuration():
    """Kiểm tra cấu hình kênh Redis Pub/Sub: channel 'agent:state' phải có mặt trong danh sách lắng nghe"""
    assert "agent:state" in _CHANNELS
    assert "agent:state" in _AGENT_CHANNELS
    assert "governor:consensus" in _AGENT_CHANNELS
    assert "market:circuit_breaker" in _AGENT_CHANNELS


@pytest.mark.anyio
async def test_broadcast_council_state_pubsub():
    """Kiểm tra council_aggregator.broadcast_council_state() phát sóng đúng định dạng JSON qua Redis channel"""
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with session_factory() as session:
            state = await council_aggregator.aggregate_council_state(session=session, is_test=True)

        pubsub = r.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL_AGENT_STATE)

        # Đọc thông báo subscribe ban đầu
        await pubsub.get_message(timeout=1.0)

        # Phát sóng qua service
        await council_aggregator.broadcast_council_state(state)

        received = None
        for _ in range(10):
            msg = await pubsub.get_message(timeout=0.5)
            if msg and msg["type"] == "message":
                received = msg
                break
            await asyncio.sleep(0.05)

        assert received is not None
        data = json.loads(received["data"])
        assert data["type"] == "AGENT_STATE_UPDATE"
        assert "payload" in data
        assert "arbiter" in data["payload"]
        assert "sentinel" in data["payload"]
        assert "vector" in data["payload"]
        assert "scribe" in data["payload"]
    finally:
        await r.aclose()


@pytest.mark.anyio
async def test_trigger_and_broadcast_helper():
    """Kiểm tra helper trigger_and_broadcast_council_state() tự động lưu cache và phát sóng"""
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.delete(REDIS_KEY_COUNCIL_CACHE)

        state = await council_aggregator.trigger_and_broadcast_council_state(is_test=True)
        assert isinstance(state, AgentCouncilState)
        assert state.type == "AGENT_STATE_UPDATE"

        cached = await r.get(REDIS_KEY_COUNCIL_CACHE)
        assert cached is not None
        cached_data = json.loads(cached)
        assert cached_data["type"] == "AGENT_STATE_UPDATE"
        assert cached_data["payload"]["arbiter"]["permission"] in ["ALLOWED", "RESTRICTED", "BLOCKED"]
    finally:
        await r.aclose()


@pytest.mark.anyio
async def test_websocket_agents_stream_endpoint():
    """Kiểm tra endpoint WebSocket /api/v1/ws/agents tự động gửi snapshot khởi tạo và lắng nghe channel agent:state"""
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, text: str):
                self.sent_messages.append(text)
                raise WebSocketDisconnect()

        mock_ws = MockWebSocket()
        sample_payload = json.dumps({"type": "AGENT_STATE_UPDATE", "source": "test_cached_state"})
        await r.set(REDIS_KEY_COUNCIL_CACHE, sample_payload, ex=10)

        await agents_stream(mock_ws)

        assert mock_ws.accepted is True
        assert len(mock_ws.sent_messages) >= 1
        received = json.loads(mock_ws.sent_messages[0])
        assert received["type"] == "AGENT_STATE_UPDATE"
        assert received["source"] == "test_cached_state"
    finally:
        await r.aclose()


@pytest.mark.anyio
async def test_websocket_market_stream_sends_cached_state():
    """Kiểm tra endpoint WebSocket /api/v1/ws/market gửi snapshot council state khi client kết nối"""
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, text: str):
                self.sent_messages.append(text)
                raise WebSocketDisconnect()

        mock_ws = MockWebSocket()
        sample_payload = json.dumps({"type": "AGENT_STATE_UPDATE", "source": "market_cached_state"})
        await r.set(REDIS_KEY_COUNCIL_CACHE, sample_payload, ex=10)

        await market_stream(mock_ws)

        assert mock_ws.accepted is True
        assert len(mock_ws.sent_messages) >= 1
        received = json.loads(mock_ws.sent_messages[0])
        assert received["type"] == "AGENT_STATE_UPDATE"
        assert received["source"] == "market_cached_state"
    finally:
        await r.aclose()
