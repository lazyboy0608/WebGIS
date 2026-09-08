import asyncio
from typing import Dict, Set
from fastapi import WebSocket

from app.core.task_manager import SegyTaskStatus, get_task_manager


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts real-time task progress."""

    _instance = None

    def __new__(cls) -> "WebSocketManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_connections: Dict[str, Set[WebSocket]] = {}
            task_mgr = get_task_manager()
            task_mgr.add_listener(cls._instance._on_task_update)
        return cls._instance

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)

    def disconnect(self, client_id: str, websocket: WebSocket) -> None:
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast_to_client(self, client_id: str, message: dict) -> None:
        if client_id in self.active_connections:
            for connection in list(self.active_connections[client_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(client_id, connection)

    async def broadcast_all(self, message: dict) -> None:
        for client_id, connections in list(self.active_connections.items()):
            for connection in list(connections):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(client_id, connection)

    def _on_task_update(self, task: SegyTaskStatus) -> None:
        payload = {
            "type": "SEGY_PROGRESS_UPDATE",
            "task_id": task.task_id,
            "filename": task.filename,
            "status": task.status,
            "progress_percent": task.progress_percent,
            "message": task.message,
            "result": task.result,
            "error": task.error,
            "timestamp": task.updated_at,
        }

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self.broadcast_all(payload))
        except RuntimeError:
            pass


ws_manager = WebSocketManager()
