import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.infrastructure.storage.minio_file_storage import MinioFileStorage


@pytest.fixture
def mock_minio_client():
    client = MagicMock()
    client.bucket_exists.return_value = True
    return client


def test_minio_storage_initializes_and_creates_bucket_if_missing(tmp_path: Path):
    client = MagicMock()
    client.bucket_exists.return_value = False

    MinioFileStorage(
        bucket_name="custom-bucket",
        client=client,
        temp_dir=tmp_path,
    )

    client.bucket_exists.assert_called_once_with("custom-bucket")
    client.make_bucket.assert_called_once_with("custom-bucket")


def test_minio_storage_save(mock_minio_client, tmp_path: Path):
    storage = MinioFileStorage(
        bucket_name="raw-segy",
        client=mock_minio_client,
        temp_dir=tmp_path,
    )

    content = b"TEST SEG-Y MINIO CONTENT"
    stored_path = storage.save("line_01.sgy", content)

    # Object name should contain clean name and uploads prefix
    assert stored_path.as_posix().startswith("uploads/")
    assert "line_01.sgy" in stored_path.as_posix()


    # Verify put_object was called
    mock_minio_client.put_object.assert_called_once()
    call_args = mock_minio_client.put_object.call_args[1]
    assert call_args["bucket_name"] == "raw-segy"
    assert call_args["object_name"] == str(stored_path).replace("\\", "/")
    assert call_args["length"] == len(content)


def test_minio_storage_get_path_local_cache(mock_minio_client, tmp_path: Path):
    storage = MinioFileStorage(
        bucket_name="raw-segy",
        client=mock_minio_client,
        temp_dir=tmp_path,
    )

    content = b"CACHED SEG-Y CONTENT"
    stored_path = storage.save("line_02.sgy", content)

    # get_path should return local cached file path
    local_path = storage.get_path(str(stored_path))

    assert isinstance(local_path, Path)
    assert local_path.exists()
    assert local_path.read_bytes() == content


def test_minio_storage_get_path_download_if_not_cached(mock_minio_client, tmp_path: Path):
    storage = MinioFileStorage(
        bucket_name="raw-segy",
        client=mock_minio_client,
        temp_dir=tmp_path,
    )

    object_name = "uploads/abc123_remote.sgy"

    def side_effect_fget(bucket_name, object_name, file_path):
        Path(file_path).write_bytes(b"DOWNLOADED SGY")

    mock_minio_client.fget_object.side_effect = side_effect_fget

    local_path = storage.get_path(object_name)

    assert local_path.exists()
    assert local_path.read_bytes() == b"DOWNLOADED SGY"
    mock_minio_client.fget_object.assert_called_once_with(
        bucket_name="raw-segy",
        object_name=object_name,
        file_path=str(local_path),
    )


def test_minio_storage_delete(mock_minio_client, tmp_path: Path):
    storage = MinioFileStorage(
        bucket_name="raw-segy",
        client=mock_minio_client,
        temp_dir=tmp_path,
    )

    stored_path = storage.save("to_delete.sgy", b"DELETE ME")
    local_path = storage.get_path(str(stored_path))
    assert local_path.exists()

    storage.delete(stored_path)

    mock_minio_client.remove_object.assert_called_once_with(
        bucket_name="raw-segy",
        object_name=str(stored_path).replace("\\", "/"),
    )
    assert not local_path.exists()


def test_minio_presigned_download_url(mock_minio_client, tmp_path: Path):
    storage = MinioFileStorage(
        bucket_name="raw-segy",
        client=mock_minio_client,
        temp_dir=tmp_path,
    )

    mock_minio_client.presigned_get_object.return_value = "https://minio.local/raw-segy/obj?token=123"

    url = storage.get_presigned_download_url("uploads/test.sgy", expires_seconds=1800)

    assert url == "https://minio.local/raw-segy/obj?token=123"
    mock_minio_client.presigned_get_object.assert_called_once()
