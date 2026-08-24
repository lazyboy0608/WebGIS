from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.coordinate import Coordinate
from app.domain.models.segy_file import SegyFile


class SegyFileRepository(ABC):
    """Repository interface for SEG-Y files."""

    @abstractmethod
    def create(self, segy_file: SegyFile) -> SegyFile:
        """Persist a new SEG-Y file."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, file_id: int) -> Optional[SegyFile]:
        """Get a SEG-Y file by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_filename(self, filename: str) -> Optional[SegyFile]:
        """Get a SEG-Y file by filename."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[SegyFile]:
        """Return all SEG-Y files."""
        raise NotImplementedError

    @abstractmethod
    def update(self, segy_file: SegyFile) -> SegyFile:
        """Update an existing SEG-Y file."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, file_id: int) -> None:
        """Delete a SEG-Y file."""
        raise NotImplementedError

    @abstractmethod
    def intersects_polygon(self, polygon):
        """Find SEG-Y files intersecting a polygon."""
        raise NotImplementedError

    @abstractmethod
    def update_geometry(
        self,
        file_id: int,
        coordinates: list[list[Coordinate]],
    ) -> SegyFile:
        """Update the processed geometry for a SEG-Y file."""
        raise NotImplementedError
