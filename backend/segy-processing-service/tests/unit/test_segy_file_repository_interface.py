import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.segy_file import SegyFile
from app.domain.repositories.segy_file_repository import (
    SegyFileRepository,
)


def test_repository_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        SegyFileRepository()


def test_repository_interface_requires_create():
    class IncompleteRepository(SegyFileRepository):
        pass

    with pytest.raises(TypeError):
        IncompleteRepository()


def test_repository_interface_can_be_implemented():
    class FakeSegyFileRepository(SegyFileRepository):

        def create(self, segy_file: SegyFile) -> SegyFile:
            return segy_file

        def get_by_id(self, file_id: int):
            return None

        def get_by_filename(self, filename: str):
            return None

        def list_all(self):
            return []

        def update(self, segy_file: SegyFile) -> SegyFile:
            return segy_file

        def delete(self, file_id: int) -> None:
            pass

        def intersects_polygon(self, polygon):
            return []

        def update_geometry(
            self,
            file_id: int,
            coordinates: list[Coordinate],
        ) -> SegyFile:
            raise NotImplementedError

    repository = FakeSegyFileRepository()

    assert repository is not None
