"WebSocket connection manager for research.status events."
import anyio
import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[channel].add(websocket)

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        async with self._lock:
            self._connections[channel].discard(websocket)

    async def broadcast(self, channel: str, event: str, data: dict) -> None:
        message = json.dumps({"event": event, "data": data}, default=str)
        async with self._lock:
            sockets = list(self._connections.get(channel, set()))
        for websocket in sockets:
            try:
                await websocket.send_text(message)
            except Exception:
                await self.disconnect(websocket, channel)


manager = ConnectionManager()


def notify_research_status(job_payload: dict) -> None:
    """Best-effort push of research.status to connected clients (sync context)."""

    async def _send() -> None:
        await manager.broadcast("research", "research.status", job_payload)

    try:
        anyio.from_thread.run(_send)
    except RuntimeError:
        pass  # no async worker context (scripts/tests): event skipped


@router.websocket("/api/v1/ws/{channel}")
async def websocket_channel(websocket: WebSocket, channel: str):
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()  # keepalive; server is push-only
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
