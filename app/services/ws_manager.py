import json
import logging
import uuid

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        self._connections: dict[uuid.UUID, list[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(f"WS connected: user={user_id}, total={len(self._connections[user_id])}")

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self._connections.pop(user_id, None)
        logger.info(f"WS disconnected: user={user_id}")

    async def send_to_user(self, user_id: uuid.UUID, message: dict) -> None:
        connections = self._connections.get(user_id, [])
        logger.info(f"WS send_to_user: user={user_id}, connections={len(connections)}, type={message.get('type')}")
        payload = json.dumps(message, default=str)
        dead = []
        for ws in connections:
            try:
                await ws.send_text(payload)
                logger.info(f"WS sent to user={user_id}")
            except Exception as e:
                logger.warning(f"WS send failed for user={user_id}: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_to_users(self, user_ids: list[uuid.UUID], message: dict) -> None:
        for user_id in user_ids:
            await self.send_to_user(user_id, message)


ws_manager = ConnectionManager()
