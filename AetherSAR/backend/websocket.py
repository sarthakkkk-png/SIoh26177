"""
AetherSAR Phase 5 - WebSocket connection manager.

A simple in-memory hub: each mission has a set of connected WebSockets
(a future dashboard). Broadcast is best-effort: a broken client connection
is dropped and never crashes the backend. Not a distributed event system.
"""

from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, mission_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(mission_id, set()).add(websocket)

    def disconnect(self, mission_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(mission_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                self._connections.pop(mission_id, None)

    async def broadcast(self, mission_id: str, event: dict) -> None:
        connections = list(self._connections.get(mission_id, set()))
        for websocket in connections:
            try:
                await websocket.send_json(event)
            except Exception:
                # A dead client socket must not take down the backend;
                # drop it and keep broadcasting to the remaining clients.
                self.disconnect(mission_id, websocket)


manager = ConnectionManager()


@router.websocket("/ws/missions/{mission_id}")
async def mission_websocket(websocket: WebSocket, mission_id: str) -> None:
    """Live event stream for a mission (telemetry, detections, search paths)."""
    await manager.connect(mission_id, websocket)
    try:
        while True:
            # Keep the connection open; inbound client messages are ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(mission_id, websocket)