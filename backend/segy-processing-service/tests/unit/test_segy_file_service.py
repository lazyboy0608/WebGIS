from unittest.mock import Mock

from app.domain.models.segy_file import SegyFile
from app.domain.repositories.segy_file_repository import (
    SegyFileRepository,
)
from app.domain.services.file_storage import FileStorage
from app.services.segy_file_service import SegyFileService


def test_service_accepts_repository_and_file_storage_dependencies():
    repository = Mock()
    file_storage = Mock(spec=FileStorage)

    service = SegyFileService(
        repository,
        file_storage,
    )

    assert service.repository is repository
    assert service.file_storage is file_storage