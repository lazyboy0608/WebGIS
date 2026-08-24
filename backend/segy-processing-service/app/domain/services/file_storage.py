from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    """Abstraction for SEG-Y file storage."""

    @abstractmethod
    def save(
        self,
        filename: str,
        content: bytes,
    ) -> Path:
        """Save file content and return its stored path."""
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        path: Path,
    ) -> None:
        """Delete a stored file."""
        raise NotImplementedError

    @abstractmethod
    def get_path(
        self,
        filename: str,
    ) -> Path:
        """Resolve a stored filename to its path."""
        raise NotImplementedError