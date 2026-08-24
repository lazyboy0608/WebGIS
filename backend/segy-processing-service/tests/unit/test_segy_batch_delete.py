from unittest.mock import Mock
from pathlib import Path

from app.application.services.segy_file import SegyFileService
from app.domain.models.segy_file import SegyFile


def test_segy_file_service_delete_file_cleans_storage():
    repository = Mock()
    file_storage = Mock()
    service = SegyFileService(repository=repository, file_storage=file_storage)

    mock_file = SegyFile(
        id=1,
        filename="test.sgy",
        file_path="/storage/segy/test.sgy",
        file_size=100,
        source_crs="EPSG:4326",
        trace_count=10,
        line_count=1,
    )
    repository.get_by_id.return_value = mock_file

    service.delete_file(1)

    repository.get_by_id.assert_called_once_with(1)
    file_storage.delete.assert_called_once_with(Path("/storage/segy/test.sgy"))
    repository.delete.assert_called_once_with(1)


def test_segy_file_service_delete_files_batch():
    repository = Mock()
    file_storage = Mock()
    service = SegyFileService(repository=repository, file_storage=file_storage)

    file1 = SegyFile(id=1, filename="1.sgy", file_path="/storage/1.sgy", file_size=10, source_crs="EPSG:4326", trace_count=1, line_count=1)
    file2 = SegyFile(id=2, filename="2.sgy", file_path="/storage/2.sgy", file_size=20, source_crs="EPSG:4326", trace_count=1, line_count=1)

    def get_by_id_side_effect(file_id):
        if file_id == 1:
            return file1
        if file_id == 2:
            return file2
        return None

    repository.get_by_id.side_effect = get_by_id_side_effect

    deleted_ids = service.delete_files([1, 2, 3])

    assert deleted_ids == [1, 2]
    assert file_storage.delete.call_count == 2
    assert repository.delete.call_count == 2
