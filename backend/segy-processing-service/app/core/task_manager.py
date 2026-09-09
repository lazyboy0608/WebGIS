import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.core.redis_client import redis_task_client

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SegyTaskStatus:
    task_id: str
    filename: str
    status: str  # "PENDING", "UPLOADING", "PROCESSING", "COMPLETED", "FAILED"
    progress_percent: int = 0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SegyTaskStatus":
        return cls(
            task_id=data.get("task_id", ""),
            filename=data.get("filename", ""),
            status=data.get("status", "PENDING"),
            progress_percent=data.get("progress_percent", 0),
            message=data.get("message", ""),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


class TaskManager:
    """Thread-safe Task Manager for tracking async SEG-Y processing status with Redis integration."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "TaskManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, SegyTaskStatus] = {}
                    cls._instance._listeners: list[Callable[[SegyTaskStatus], None]] = []
        return cls._instance

    def _sync_to_redis(self, task: SegyTaskStatus) -> None:
        if not redis_task_client.is_available():
            return
        try:
            payload = task.to_dict()
            redis_task_client.set_json(f"task:{task.task_id}", payload, ttl=86400)
            redis_task_client.publish("segy_task_updates", payload)
        except Exception as e:
            logger.warning(f"Failed to sync task {task.task_id} to Redis: {e}")

    def create_task(self, task_id: str, filename: str) -> SegyTaskStatus:
        task = SegyTaskStatus(
            task_id=task_id,
            filename=filename,
            status="PENDING",
            progress_percent=0,
            message="Task created",
        )
        with self._lock:
            self._tasks[task_id] = task
        self._sync_to_redis(task)
        self._notify(task)
        return task

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress_percent: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[SegyTaskStatus]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                if redis_task_client.is_available():
                    cached = redis_task_client.get_json(f"task:{task_id}")
                    if cached:
                        task = SegyTaskStatus.from_dict(cached)
                        self._tasks[task_id] = task
            if not task:
                return None
            if status is not None:
                task.status = status
            if progress_percent is not None:
                task.progress_percent = progress_percent
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            task.updated_at = _now_iso()
            updated_copy = task

        self._sync_to_redis(updated_copy)
        self._notify(updated_copy)
        return updated_copy

    def get_task(self, task_id: str) -> Optional[SegyTaskStatus]:
        with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id]
        if redis_task_client.is_available():
            cached = redis_task_client.get_json(f"task:{task_id}")
            if cached:
                task = SegyTaskStatus.from_dict(cached)
                with self._lock:
                    self._tasks[task_id] = task
                return task
        return None

    def add_listener(self, listener: Callable[[SegyTaskStatus], None]) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def _notify(self, task: SegyTaskStatus) -> None:
        for listener in list(self._listeners):
            try:
                listener(task)
            except Exception:
                pass


def get_task_manager() -> TaskManager:
    return TaskManager()
