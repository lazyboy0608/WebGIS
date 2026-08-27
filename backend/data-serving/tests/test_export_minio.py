from unittest.mock import MagicMock
from app.infrastructure.storage.minio_client import MinioClientManager
from app.services.export_service import ExportService
from app.models import SegyFileModel, SeismicTraceModel


def test_minio_client_manager_upload_and_presigned_url():
    mock_minio = MagicMock()
    mock_minio.bucket_exists.return_value = True
    mock_minio.presigned_get_object.return_value = "https://minio.test/processed-segy/obj.csv?token=xyz"

    client_manager = MinioClientManager(client=mock_minio)

    obj_name = client_manager.upload_bytes(
        bucket_name="processed-segy",
        object_name="exports/1/sample.csv",
        data=b"col1,col2\n1,2",
        content_type="text/csv",
    )

    assert obj_name == "exports/1/sample.csv"
    mock_minio.put_object.assert_called_once()

    url = client_manager.get_presigned_download_url(
        bucket_name="processed-segy",
        object_name="exports/1/sample.csv",
        filename="sample.csv",
    )

    assert url == "https://minio.test/processed-segy/obj.csv?token=xyz"
    mock_minio.presigned_get_object.assert_called_once()


def test_export_service_raw_file_download_url():
    mock_session = MagicMock()
    mock_segy = SegyFileModel(
        id=10,
        filename="survey_2026.sgy",
        file_path="uploads/uuid_survey_2026.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=1,
    )
    mock_session.get.return_value = mock_segy

    mock_storage = MagicMock()
    mock_storage.get_presigned_download_url.return_value = "https://minio.test/raw-segy/obj?token=raw"

    service = ExportService(session=mock_session, storage_manager=mock_storage)
    result = service.get_raw_file_download_url(10)

    assert result["segy_file_id"] == 10
    assert result["filename"] == "survey_2026.sgy"
    assert result["object_name"] == "uploads/uuid_survey_2026.sgy"
    assert result["download_url"] == "https://minio.test/raw-segy/obj?token=raw"
