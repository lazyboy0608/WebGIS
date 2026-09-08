from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


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

    def save_stream(
        self,
        filename: str,
        stream: BinaryIO,
        length: int,
    ) -> Path:
        """Save file stream and return its stored path."""
        # Default fallback reads stream content if not overridden
        return self.save(filename, stream.read())


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