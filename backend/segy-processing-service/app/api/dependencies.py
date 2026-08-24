from collections.abc import Generator
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.services.processing_persistence import (
    ProcessingResultPersistenceService,
)
from app.application.services.processed_data_query import ProcessedDataQueryService
from app.application.services.segy_file import SegyFileService
from app.application.services.segy_processing import SegyProcessingService
from app.application.use_cases.process_segy_file_use_case import (
    ProcessSegyFileUseCase,
)
from app.domain.models.crs import SOURCE_CRS
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
from app.infrastructure.segy.segyio_reader import SegyIOReader
from app.infrastructure.storage.local_file_storage import (
    LocalFileStorage,
)
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.crs_transformer import CRSTransformer
from app.services.line_builder import LineBuilder
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.segy_reader import SegyReaderService
from app.services.segy_validator import SegyValidator
from app.services.shot_point_analyzer import ShotPointAnalyzer
from app.services.trace_processor import TraceProcessor
from app.services.wgs84_line_geometry_builder import WGS84LineGeometryBuilder


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_segy_file_repository(
    session: Session = Depends(get_db_session),
) -> SQLAlchemySegyFileRepository:
    return SQLAlchemySegyFileRepository(session)


def get_file_storage() -> LocalFileStorage:
    return LocalFileStorage(Path("storage/segy"))


def get_segy_file_service(
    repository: SQLAlchemySegyFileRepository = Depends(get_segy_file_repository),
    file_storage: LocalFileStorage = Depends(get_file_storage),
) -> SegyFileService:
    return SegyFileService(
        repository,
        file_storage,
    )


def get_process_segy_file_use_case(
    session: Session = Depends(get_db_session),
    file_storage: LocalFileStorage = Depends(get_file_storage),
) -> ProcessSegyFileUseCase:
    coordinate_transformer = CoordinateTransformer()
    processing_service = SegyProcessingService(
        segy_reader=SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        ),
        trace_processor=TraceProcessor(coordinate_transformer),
        shot_point_analyzer=ShotPointAnalyzer(coordinate_transformer),
        line_builder=LineBuilder(),
        topology_analyzer=LineTopologyAnalyzer(),
        wgs84_geometry_builder=WGS84LineGeometryBuilder(
            CRSTransformer(SOURCE_CRS),
        ),
        file_storage=file_storage,
    )
    persistence_service = ProcessingResultPersistenceService(
        line_repository=SQLAlchemyLineRepository(session),
        shot_point_repository=SQLAlchemyShotPointRepository(session),
        trace_repository=SQLAlchemySeismicTraceRepository(session),
        segy_file_repository=SQLAlchemySegyFileRepository(session),
    )
    return ProcessSegyFileUseCase(
        processing_service=processing_service,
        persistence_service=persistence_service,
    )


def get_processed_data_query_service(
    session: Session = Depends(get_db_session),
) -> ProcessedDataQueryService:
    return ProcessedDataQueryService(session)
