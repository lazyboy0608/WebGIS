from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.domain.models.coordinate import Coordinate
from app.domain.models.processed_segy_data import ProcessedSegyData
from app.domain.models.segy_file import SegyFile
from app.domain.models.seismic_line import SeismicLine
from app.domain.models.shot_point import ShotPoint
from app.domain.models.trace import ProcessedTrace, SourcePoint
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)
from app.infrastructure.database.repositories.seismic_line_repository import (
    SQLAlchemyLineRepository,
)
from app.infrastructure.database.repositories.seismic_shot_point_repository import (
    SQLAlchemyShotPointRepository,
)
from app.infrastructure.database.repositories.seismic_trace_repository import (
    SQLAlchemySeismicTraceRepository,
)
from app.infrastructure.database.session import SessionLocal
from app.main import app
from app.services.processing_result_persistence_service import (
    ProcessingResultPersistenceService,
)

client = TestClient(app)


def test_read_processed_data_from_postgis() -> None:
    session = SessionLocal()
    file_id = None

    try:
        coordinates = [
            Coordinate(x=-90.1, y=30.1),
            Coordinate(x=-90.2, y=30.2),
        ]
        file = SQLAlchemySegyFileRepository(session).create(
            SegyFile(
                filename=f"processed-{uuid4()}.sgy",
                file_path="storage/segy/test.sgy",
                file_size=100,
                source_crs="EPSG:26782",
                trace_count=2,
                line_count=1,
            )
        )
        file_id = file.id
        assert file_id is not None

        persistence = ProcessingResultPersistenceService(
            line_repository=SQLAlchemyLineRepository(session),
            shot_point_repository=SQLAlchemyShotPointRepository(session),
            trace_repository=SQLAlchemySeismicTraceRepository(session),
        )
        persistence.persist(
            ProcessedSegyData(
                metadata=None,
                processed_traces=[
                    ProcessedTrace(
                        trace_index=0,
                        source_point=SourcePoint(number=100),
                        coordinate=coordinates[0],
                        wgs84_coordinate=coordinates[0],
                    ),
                    ProcessedTrace(
                        trace_index=1,
                        source_point=SourcePoint(number=101),
                        coordinate=coordinates[1],
                        wgs84_coordinate=coordinates[1],
                    ),
                ],
                line=SeismicLine(
                    line_id="TEST-LINE",
                    coordinates=coordinates,
                ),
                shot_point_analysis=type(
                    "ShotPointAnalysisStub",
                    (),
                    {
                        "shot_points": [
                            ShotPoint(
                                number=100,
                                trace_indices=[0],
                                coordinates=[coordinates[0]],
                            ),
                            ShotPoint(
                                number=101,
                                trace_indices=[1],
                                coordinates=[coordinates[1]],
                            ),
                        ]
                    },
                )(),
            ),
            file_id,
        )
        session.commit()

        summary = client.get(f"/api/segy-files/{file_id}/processed/summary")
        line = client.get(f"/api/segy-files/{file_id}/processed/line")
        shot_points = client.get(
            f"/api/segy-files/{file_id}/processed/shot-points?limit=1"
        )
        traces = client.get(f"/api/segy-files/{file_id}/processed/traces")

        assert summary.status_code == 200
        assert summary.json()["processed_trace_count"] == 2
        assert line.status_code == 200
        assert line.json()["geometry"]["type"] == "LineString"
        assert line.json()["properties"]["srid"] == 4326
        assert shot_points.status_code == 200
        assert len(shot_points.json()["features"]) == 1
        assert traces.status_code == 200
        assert len(traces.json()["features"]) == 2
    finally:
        if file_id is not None:
            session.execute(
                text("DELETE FROM segy_files WHERE id = :file_id"),
                {"file_id": file_id},
            )
            session.commit()
        session.close()
