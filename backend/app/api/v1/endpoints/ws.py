from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.core.redis_client import redis_client

router = APIRouter()

@router.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    await websocket.accept()
    client = redis_client.get_client()
    pubsub = client.pubsub()
    await pubsub.subscribe("clickguard:decisions")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe("clickguard:decisions")