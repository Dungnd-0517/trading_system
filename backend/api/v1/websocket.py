from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.redis_client import client

router = APIRouter()
_CHANNELS = (
    "market:ticks",
    "paper:orders",
    "news:events",
    "market:signals",
    "market:circuit_breaker",
    "governor:consensus",
    "agent:trader:dialogue",
    "governor:approval_response",
    "agent:state",
)

_AGENT_CHANNELS = (
    "agent:state",
    "governor:consensus",
    "market:circuit_breaker",
    "agent:trader:dialogue",
    "governor:approval_response",
)


@router.websocket("/ws/market")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    subscription = client.pubsub()
    await subscription.subscribe(*_CHANNELS)
    try:
        # Gửi ngay snapshot council state gần nhất nếu có trong cache để hydrate tức thì
        try:
            cached_council = await client.get("runtime:agent_council_state")
            if cached_council:
                await websocket.send_text(cached_council)
        except WebSocketDisconnect:
            raise
        except Exception:
            pass

        async for message in subscription.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await subscription.unsubscribe(*_CHANNELS)
            await subscription.aclose()
        except Exception:
            pass


@router.websocket("/ws/agents")
async def agents_stream(websocket: WebSocket) -> None:
    """
    Dedicated WebSocket endpoint cho Agent Council Deck & Real-time Intelligence Stream.
    Lắng nghe tập trung các kênh: 'agent:state', 'governor:consensus',
    'market:circuit_breaker', 'agent:trader:dialogue'.
    """
    await websocket.accept()
    subscription = client.pubsub()
    await subscription.subscribe(*_AGENT_CHANNELS)
    try:
        # Gửi ngay snapshot council state gần nhất nếu có trong cache để hydrate tức thì
        try:
            cached_council = await client.get("runtime:agent_council_state")
            if cached_council:
                await websocket.send_text(cached_council)
        except WebSocketDisconnect:
            raise
        except Exception:
            pass

        async for message in subscription.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await subscription.unsubscribe(*_AGENT_CHANNELS)
            await subscription.aclose()
        except Exception:
            pass
