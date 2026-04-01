import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Fan-out apenas para conexões do mesmo user_id (correção vs broadcast global Encore)."""

    def __init__(self) -> None:
        self._by_user: dict[int, list[WebSocket]] = {}

    async def register(self, user_id: int, websocket: WebSocket) -> None:
        self._by_user.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        conns = self._by_user.get(user_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            del self._by_user[user_id]

    async def broadcast_user(self, user_id: int, payload: dict[str, Any]) -> None:
        for ws in list(self._by_user.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                logger.debug("Removing dead websocket for user %s", user_id)
                self.disconnect(user_id, ws)


manager = ConnectionManager()
