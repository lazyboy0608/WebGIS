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
from app.services.processing_result_persistence_service import (
    ProcessingResultPersistenceService,
)


def test_processing_result_persistence_flow() -> None:
    """
    Integration test for the complete persistence flow.

    Verifies that:

    1. a SEG-Y file exists as the parent record;
    2. the processing service persists a seismic line;
    3. shot points are persisted;
    4. traces are persisted;
    5. trace -> shot point relationships are resolved;
    6. PostGIS geometries are actually stored.
    """

    session = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Create parent SEG-Y file
        # ---------------------------------------------------------

        segy_file_repository = SQLAlchemySegyFileRepository(
            session
        )

        segy_file = SegyFile(
            filename="integration-test.sgy",
            file_path="/tmp/integration-test.sgy",
            file_size=1024,
            source_crs="EPSG:32606",
            trace_count=3,
            line_count=1,
            geometry=None,
        )

        saved_file = segy_file_repository.create(
            segy_file
        )

        assert saved_file.id is not None

        segy_file_id = saved_file.id

        # ---------------------------------------------------------
        # 2. Create repositories
        # ---------------------------------------------------------

        line_repository = SQLAlchemyLineRepository(
            session
        )

        shot_point_repository = (
            SQLAlchemyShotPointRepository(session)
        )

        trace_repository = SQLAlchemySeismicTraceRepository(
            session
        )

        # ---------------------------------------------------------
        # 3. Create persistence service
        # ---------------------------------------------------------

        persistence_service = (
            ProcessingResultPersistenceService(
                line_repository=line_repository,
                shot_point_repository=shot_point_repository,
                trace_repository=trace_repository,
                segy_file_repository=segy_file_repository,
            )
        )

        # ---------------------------------------------------------
        # 4. Prepare processed SEG-Y result
        # ---------------------------------------------------------

        coordinates = [
            Coordinate(
                x=100.0,
                y=200.0,
            ),
            Coordinate(
                x=110.0,
                y=200.0,
            ),
            Coordinate(
                x=120.0,
                y=200.0,
            ),
        ]

        line = SeismicLine(
            line_id="LINE-1",
            coordinates=coordinates,
        )

        shot_point_100 = ShotPoint(
            number=100,
            trace_indices=[0, 1],
            coordinates=[
                coordinates[0],
                coordinates[1],
            ],
        )

        shot_point_101 = ShotPoint(
            number=101,
            trace_indices=[2],
            coordinates=[
                coordinates[2],
            ],
        )

        processed_traces = [
            ProcessedTrace(
                trace_index=0,
                source_point=SourcePoint(number=100),
                coordinate=coordinates[0],
                samples=[1.0, 2.0, 3.0],
            ),
            ProcessedTrace(
                trace_index=1,
                source_point=SourcePoint(number=100),
                coordinate=coordinates[1],
                samples=[4.0, 5.0, 6.0],
            ),
            ProcessedTrace(
                trace_index=2,
                source_point=SourcePoint(number=101),
                coordinate=coordinates[2],
                samples=[7.0, 8.0, 9.0],
            ),
        ]

        processed_data = ProcessedSegyData(
            metadata=None,
            processed_traces=processed_traces,
            shot_point_analysis=None,
            line=None,
        )

        # ---------------------------------------------------------
        # 5. Replace the processing-result placeholders with
        #    the actual application-level result expected by
        #    ProcessingResultPersistenceService.
        # ---------------------------------------------------------

        processed_data.line = line

        # The service expects shot_point_analysis.shot_points.
        #
        # If ShotPointAnalysis is immutable in your project,
        # construct it directly instead of assigning this way.
        processed_data.shot_point_analysis = type(
            "ShotPointAnalysisStub",
            (),
            {
                "shot_points": [
                    shot_point_100,
                    shot_point_101,
                ]
            },
        )()

        # ---------------------------------------------------------
        # 6. Persist
        # ---------------------------------------------------------

        persistence_service.persist(
            processed_data,
            segy_file_id,
            line_id="LINE-1",
        )

        # ---------------------------------------------------------
        # 7. Flush so all SQL statements are executed
        # ---------------------------------------------------------

        session.flush()

        # ---------------------------------------------------------
        # 8. Verify seismic line
        # ---------------------------------------------------------

        line_count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM seismic_lines
                WHERE segy_file_id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert line_count == 1

        # ---------------------------------------------------------
        # 9. Verify shot points
        # ---------------------------------------------------------

        shot_point_count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM seismic_shot_points
                WHERE segy_file_id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert shot_point_count == 2

        # ---------------------------------------------------------
        # 10. Verify traces
        # ---------------------------------------------------------

        trace_count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM seismic_traces
                WHERE segy_file_id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert trace_count == 3

        # ---------------------------------------------------------
        # 11. Verify trace -> shot point relationship
        # ---------------------------------------------------------

        relationships = session.execute(
            text(
                """
                SELECT
                    t.trace_index,
                    sp.shot_point_number
                FROM seismic_traces t
                JOIN seismic_shot_points sp
                    ON t.shot_point_id = sp.id
                WHERE t.segy_file_id = :file_id
                ORDER BY t.trace_index
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).all()

        assert relationships == [
            (0, 100),
            (1, 100),
            (2, 101),
        ]

        # ---------------------------------------------------------
        # 12. Verify line geometry
        # ---------------------------------------------------------

        line_geometry = session.execute(
            text(
                """
                SELECT ST_GeometryType(geometry)
                FROM seismic_lines
                WHERE segy_file_id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert line_geometry == "ST_LineString"

        # ---------------------------------------------------------
        # 13. Verify trace geometry
        # ---------------------------------------------------------

        trace_geometry_count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM seismic_traces
                WHERE segy_file_id = :file_id
                  AND geometry IS NOT NULL
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert trace_geometry_count == 3

        # ---------------------------------------------------------
        # 14. Verify shot point geometry
        # ---------------------------------------------------------

        shot_point_geometry_count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM seismic_shot_points
                WHERE segy_file_id = :file_id
                  AND geometry IS NOT NULL
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert shot_point_geometry_count == 2

        # ---------------------------------------------------------
        # 15. Verify SRID
        # ---------------------------------------------------------

        line_srid = session.execute(
            text(
                """
                SELECT ST_SRID(geometry)
                FROM seismic_lines
                WHERE segy_file_id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).scalar_one()

        assert line_srid == 4326

        # ---------------------------------------------------------
        # 16. Verify parent SEG-Y file geometry
        # ---------------------------------------------------------

        file_geometry = session.execute(
            text(
                """
                SELECT ST_GeometryType(geometry), ST_SRID(geometry)
                FROM segy_files
                WHERE id = :file_id
                """
            ),
            {
                "file_id": segy_file_id,
            },
        ).one()

        assert file_geometry == ("ST_MultiLineString", 4326)

    finally:
        session.rollback()
        session.close()
