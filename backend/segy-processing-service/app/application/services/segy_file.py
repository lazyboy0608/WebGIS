from app.domain.interfaces.repositories.segy_file_repository import (
    SegyFileRepository,
)
from app.domain.models.segy_file import SegyFile
from app.domain.services.file_storage import FileStorage


class SegyFileService:
    """Application service for SEG-Y file records."""

    def __init__(
        self,
        repository: SegyFileRepository,
        file_storage: FileStorage | None = None,
    ) -> None:
        self.repository = repository
        self.file_storage = file_storage

    def create_file(self, segy_file: SegyFile) -> SegyFile:
        return self.repository.create(segy_file)

    def get_file(self, file_id: int) -> SegyFile | None:
        return self.repository.get_by_id(file_id)

    def get_file_by_filename(self, filename: str) -> SegyFile | None:
        return self.repository.get_by_filename(filename)

    def list_files(self) -> list[SegyFile]:
        return self.repository.list_all()

    def update_file(self, segy_file: SegyFile) -> SegyFile:
        return self.repository.update(segy_file)

    def delete_file(self, file_id: int) -> None:
        self.repository.delete(file_id)

    def find_files_intersecting_polygon(self, polygon) -> list[SegyFile]:
        return self.repository.intersects_polygon(polygon)
