import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate via query param: ws://host/api/ws?token=<jwt>
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = uuid.UUID(payload["sub"])
    connected_at = time.time()
    await ws_manager.connect(user_id, websocket)

    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect as e:
        duration = round(time.time() - connected_at, 1)
        logger.info("WS closed: user=%s code=%s reason=%s duration=%ss", user_id, e.code, e.reason, duration)
        ws_manager.disconnect(user_id, websocket)
    except Exception as e:
        duration = round(time.time() - connected_at, 1)
        logger.warning("WS error: user=%s error=%s duration=%ss", user_id, e, duration)
        ws_manager.disconnect(user_id, websocket)
