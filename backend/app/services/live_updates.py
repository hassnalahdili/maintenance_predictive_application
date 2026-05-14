from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class LiveUpdatesManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale_clients: list[WebSocket] = []
        for client in list(self._clients):
            try:
                await client.send_json(payload)
            except Exception:
                stale_clients.append(client)
        for client in stale_clients:
            self.disconnect(client)


manager = LiveUpdatesManager()
_loop: asyncio.AbstractEventLoop | None = None


def configure_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def publish_event(event_type: str, **payload: Any) -> None:
    if _loop is None:
        return
    message = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **payload,
    }
    asyncio.run_coroutine_threadsafe(manager.broadcast(message), _loop)
