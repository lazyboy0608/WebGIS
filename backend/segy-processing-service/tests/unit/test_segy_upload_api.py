from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_file_storage,
    get_processed_data_query_service,
    get_process_segy_file_use_case,
    get_segy_file_service,
)
from app.domain.models.coordinate import Coordinate
from app.domain.models.segy_file import SegyFile
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEGY_FILE = PROJECT_ROOT / "data" / "input" / "slb1.sgy"


class FakeSegyFileService:
    def __init__(self, existing: SegyFile | None = None) -> None:
        self.created: SegyFile | None = None
        self.existing = existing

    def create_file(self, segy_file: SegyFile) -> SegyFile:
        self.created = segy_file
        return SegyFile(
            id=42,
            filename=segy_file.filename,
            file_path=segy_file.file_path,
            file_size=segy_file.file_size,
            source_crs=segy_file.source_crs,
            trace_count=segy_file.trace_count,
            line_count=segy_file.line_count,
            geometry=segy_file.geometry,
        )

    def get_file_by_filename(self, filename: str) -> SegyFile | None:
        if self.existing is None:
            return None
        return self.existing if self.existing.filename == filename else None


class FakeProcessedDataQueryService:
    def __init__(self, summary_result: dict[str, object] | None = None) -> None:
        self.summary_result = summary_result

    def summary(self, file_id: int):
        return self.summary_result


class FakeProcessUseCase:
    def __init__(self) -> None:
        self.arguments: dict[str, object] | None = None

    def execute(self, **kwargs):
        self.arguments = kwargs
        coordinate = Coordinate(x=1.0, y=2.0)
        return SimpleNamespace(
            processed_traces=[
                SimpleNamespace(
                    trace_index=0,
                    source_point=SimpleNamespace(number=153),
                    coordinate=coordinate,
                    wgs84_coordinate=coordinate,
                )
            ],
            shot_point_analysis=SimpleNamespace(unique_shot_point_count=1),
            line=SimpleNamespace(coordinates=[coordinate, coordinate]),
            topology_analysis=SimpleNamespace(continuous=True),
            wgs84_geometry=SimpleNamespace(srid=4326),
        )


def test_upload_segy_file_saves_file_and_starts_processing(tmp_path) -> None:
    service = FakeSegyFileService()
    use_case = FakeProcessUseCase()
    query_service = FakeProcessedDataQueryService()
    storage = LocalFileStorage(tmp_path)

    app.dependency_overrides[get_segy_file_service] = lambda: service
    app.dependency_overrides[get_process_segy_file_use_case] = lambda: use_case
    app.dependency_overrides[get_processed_data_query_service] = lambda: query_service
    app.dependency_overrides[get_file_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            with SEGY_FILE.open("rb") as file_handle:
                response = client.post(
                    "/api/segy-files/upload",
                    files={
                        "file": (
                            "slb1.sgy",
                            file_handle,
                            "application/octet-stream",
                        )
                    },
                    data={"source_crs": "EPSG:26782"},
                )

        assert response.status_code == 201
        assert response.json()["segy_file_id"] == 42
        assert response.json()["trace_count"] == 1
        assert (tmp_path / "slb1.sgy").exists()
        assert service.created is not None
        assert service.created.trace_count == 630
        assert service.created.source_crs == "EPSG:26782"
        assert use_case.arguments == {
            "filename": "slb1.sgy",
            "segy_file_id": 42,
            "source_crs": "EPSG:26782",
        }
    finally:
        app.dependency_overrides.clear()


def test_batch_upload_processes_multiple_files_without_overwriting(
    tmp_path,
) -> None:
    service = FakeSegyFileService()
    use_case = FakeProcessUseCase()
    query_service = FakeProcessedDataQueryService()
    storage = LocalFileStorage(tmp_path)

    app.dependency_overrides[get_segy_file_service] = lambda: service
    app.dependency_overrides[get_process_segy_file_use_case] = lambda: use_case
    app.dependency_overrides[get_processed_data_query_service] = lambda: query_service
    app.dependency_overrides[get_file_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            with SEGY_FILE.open("rb") as first, SEGY_FILE.open("rb") as second:
                response = client.post(
                    "/api/segy-files/upload/batch",
                    files=[
                        ("files", ("slb1_a.sgy", first, "application/octet-stream")),
                        ("files", ("slb1_b.sgy", second, "application/octet-stream")),
                    ],
                    data={"source_crs": "EPSG:26782"},
                )

        assert response.status_code == 201
        assert len(response.json()["files"]) == 2
        assert len(list(tmp_path.glob("*.sgy"))) == 2
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_filename_when_processed_file_already_exists(tmp_path) -> None:
    existing = SegyFile(
        id=5,
        filename="slb1.sgy",
        file_path="storage/segy/slb1.sgy",
        file_size=1,
        source_crs="EPSG:32605",
        trace_count=1,
        line_count=1,
    )
    service = FakeSegyFileService(existing=existing)
    use_case = FakeProcessUseCase()
    query_service = FakeProcessedDataQueryService(
        summary_result={
            "processed_line_count": 1,
            "processed_trace_count": 10,
        }
    )
    storage = LocalFileStorage(tmp_path)

    app.dependency_overrides[get_segy_file_service] = lambda: service
    app.dependency_overrides[get_process_segy_file_use_case] = lambda: use_case
    app.dependency_overrides[get_processed_data_query_service] = lambda: query_service
    app.dependency_overrides[get_file_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            with SEGY_FILE.open("rb") as file_handle:
                response = client.post(
                    "/api/segy-files/upload",
                    files={
                        "file": (
                            "slb1.sgy",
                            file_handle,
                            "application/octet-stream",
                        )
                    },
                )

        assert response.status_code == 409
        assert "same filename" in response.json()["detail"]
        assert service.created is None
        assert len(list(tmp_path.glob("*.sgy"))) == 0
    finally:
        app.dependency_overrides.clear()


def test_upload_fast_async_returns_task_id_in_sub_second(tmp_path) -> None:
    class RealStyleUseCase:
        pass

    service = FakeSegyFileService()
    use_case = RealStyleUseCase()
    query_service = FakeProcessedDataQueryService()
    storage = LocalFileStorage(tmp_path)

    app.dependency_overrides[get_segy_file_service] = lambda: service
    app.dependency_overrides[get_process_segy_file_use_case] = lambda: use_case
    app.dependency_overrides[get_processed_data_query_service] = lambda: query_service
    app.dependency_overrides[get_file_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            with SEGY_FILE.open("rb") as file_handle:
                response = client.post(
                    "/api/segy-files/upload",
                    files={
                        "file": (
                            "slb1_async.sgy",
                            file_handle,
                            "application/octet-stream",
                        )
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] is not None
        assert data["filename"] == "slb1_async.sgy"
    finally:
        app.dependency_overrides.clear()
