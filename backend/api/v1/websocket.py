from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.redis_client import client

router = APIRouter()


@router.websocket("/ws/market")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    subscription = client.pubsub()
    await subscription.subscribe("market:ticks", "paper:orders")
    try:
        async for message in subscription.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await subscription.unsubscribe("market:ticks", "paper:orders")
        await subscription.aclose()