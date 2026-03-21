import jwt
import os
import logging
from fastapi import WebSocket
from typing import Dict

logger = logging.getLogger(__name__)

LMU_APP_SECRET = os.environ.get("LMU_APP_SECRET", "")
LMU_APP_ID = os.environ.get("LMU_APP_ID", "app_3lXIxPKb")
DEV_BYPASS_AUTH = os.environ.get("DEV_BYPASS_AUTH", "").strip() == "1"


def _authenticate_ws(token: str) -> dict | None:
    """Verify JWT token for WebSocket connections. Returns user dict or None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, LMU_APP_SECRET, algorithms=["HS256"])
        if payload.get("app") != LMU_APP_ID:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


class ConnectionManager:
    """WebSocket connection manager for real-time progress updates."""

    def __init__(self):
        # Map: websocket -> user_id (or "dev_admin" for dev bypass)
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[websocket] = user_id

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast(self, message: dict, user_id: str | None = None):
        """Broadcast message. If user_id given, only send to that user's connections."""
        disconnected = []
        for conn, uid in self.active_connections.items():
            if user_id and uid != user_id:
                continue
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()
