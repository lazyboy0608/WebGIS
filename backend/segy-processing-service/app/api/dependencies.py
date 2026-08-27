from collections.abc import Generator
from pathlib import Path

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.services.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    access_token: str | None = Cookie(default=None),
) -> int | None:
    """
    Extract authenticated user_id from request.

    Tries in order:
      1. Authorization: Bearer <token>  (API clients, Swagger UI)
      2. access_token cookie            (browser frontend — credentials:'include')

    Returns None if no valid token is found (unauthenticated upload is allowed).
    """
    token: str | None = credentials.credentials if credentials else access_token
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        return int(payload["sub"])
    except (ValueError, TypeError):
        return None

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
from app.core.config import settings
from app.domain.services.file_storage import FileStorage
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.infrastructure.storage.minio_file_storage import MinioFileStorage
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


def get_file_storage() -> FileStorage:
    if settings.STORAGE_TYPE.lower() == "minio":
        return MinioFileStorage(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            bucket_name=settings.MINIO_BUCKET_RAW,
        )
    return LocalFileStorage(settings.LOCAL_STORAGE_DIR)


def get_segy_file_service(
    repository: SQLAlchemySegyFileRepository = Depends(get_segy_file_repository),
    file_storage: FileStorage = Depends(get_file_storage),
) -> SegyFileService:
    return SegyFileService(
        repository,
        file_storage,
    )


def get_process_segy_file_use_case(
    session: Session = Depends(get_db_session),
    file_storage: FileStorage = Depends(get_file_storage),
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
