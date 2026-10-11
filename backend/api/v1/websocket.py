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
)


@router.websocket("/ws/market")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    subscription = client.pubsub()
    await subscription.subscribe(*_CHANNELS)
    try:
        async for message in subscription.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await subscription.unsubscribe(*_CHANNELS)
        await subscription.aclose()