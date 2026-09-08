import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


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



class TaskManager:
    """Thread-safe Task Manager for tracking async SEG-Y processing status."""

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

        self._notify(updated_copy)
        return updated_copy

    def get_task(self, task_id: str) -> Optional[SegyTaskStatus]:
        with self._lock:
            return self._tasks.get(task_id)

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
