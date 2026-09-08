from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user_id,
    get_db_session,
    get_file_storage,
    get_processed_data_query_service,
    get_process_segy_file_use_case,
    get_segy_file_service,
)
from app.infrastructure.database.session import SessionLocal
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
from app.application.services.processing_persistence import (
    ProcessingResultPersistenceService,
)
from app.application.services.segy_processing import (
    SegyProcessingService,
)
from app.services.line_builder import LineBuilder
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.segy_validator import SegyValidator
from app.services.shot_point_analyzer import ShotPointAnalyzer
from app.services.trace_processor import TraceProcessor
from app.services.wgs84_line_geometry_builder import WGS84LineGeometryBuilder
from app.api.schemas.segy_file import (
    ProcessedPointResponse,
    SegyBatchDeleteRequest,
    SegyBatchDeleteResponse,
    SegyFileCreate,
    SegyFileResponse,
    SegyFileUpdate,
    SegyProcessingResponse,
    SegyTaskStatusResponse,
    SegyUploadBatchResponse,
)
from app.core.task_manager import get_task_manager
from app.core.websocket_manager import ws_manager
from app.application.use_cases.process_segy_file_use_case import (
    ProcessSegyFileUseCase,
)
from app.application.services.processed_data_query import ProcessedDataQueryService
from app.core.rate_limiter import UPLOAD_BATCH_MAX, UPLOAD_SINGLE_MAX, upload_rate_limit
from app.domain.models.segy_file import SegyFile
from app.domain.services.file_storage import FileStorage
from app.infrastructure.segy.segyio_reader import SegyIOReader
from app.services.segy_file_service import SegyFileService
from app.services.segy_reader import SegyReaderService
from app.services.source_crs_extractor import (
    extract_source_crs,
    validate_and_heal_source_crs,
)
from app.services.segy_validator import SegyValidator

router = APIRouter(
    prefix="/api/segy-files",
    tags=["SEG-Y Files"],
)


def _processing_response(
    result,
    file_id: int,
    filename: str,
) -> SegyProcessingResponse:
    return SegyProcessingResponse(
        segy_file_id=file_id,
        filename=filename,
        trace_count=len(result.processed_traces),
        shot_point_count=(
            result.shot_point_analysis.unique_shot_point_count
            if result.shot_point_analysis is not None
            else 0
        ),
        line_point_count=(
            len(result.line.coordinates) if result.line is not None else 0
        ),
        line_count=len(getattr(result, "lines", [])) or 1,
        topology_continuous=(
            result.topology_analysis.continuous
            if result.topology_analysis is not None
            else False
        ),
        geometry_srid=(
            result.wgs84_geometry.srid if result.wgs84_geometry is not None else None
        ),
        points=[
            ProcessedPointResponse(
                trace_index=trace.trace_index,
                shot_point=trace.source_point.number,
                x=(trace.wgs84_coordinate or trace.coordinate).x,
                y=(trace.wgs84_coordinate or trace.coordinate).y,
            )
            for trace in result.processed_traces
        ],
    )


def process_stored_file_in_background(
    task_id: str,
    filename: str,
    stored_path: Path,
    file_size: int,
    source_crs: str | None = None,
    user_id: int | None = None,
) -> None:
    """
    Background worker that runs full SEG-Y processing asynchronously (Phase 2):
    reads metadata, validates CRS, builds geometry, persists to PostGIS,
    and notifies WebSocket & TaskManager listeners.
    """
    task_mgr = get_task_manager()
    task_mgr.update_task(
        task_id,
        status="PROCESSING",
        progress_percent=35,
        message=f"File saved, reading SEG-Y metadata for {filename}...",
    )

    with SessionLocal() as db_session:
        file_storage = get_file_storage()
        segy_repo = SQLAlchemySegyFileRepository(db_session)
        service = SegyFileService(segy_repo)

        reader = SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        )
        resolved_local_path = file_storage.get_path(str(stored_path))

        try:
            metadata = reader.read_metadata(resolved_local_path)
            task_mgr.update_task(
                task_id,
                progress_percent=55,
                message="Metadata read, cross-validating CRS...",
            )

            if source_crs:
                resolved_source_crs = validate_and_heal_source_crs(
                    source_crs, file_path=resolved_local_path
                )
            else:
                resolved_source_crs = extract_source_crs(
                    metadata, file_path=resolved_local_path
                )

            segy_file = service.create_file(
                SegyFile(
                    id=None,
                    user_id=user_id,
                    filename=filename,
                    file_path=str(stored_path),
                    file_size=file_size if file_size > 0 else 1,
                    source_crs=resolved_source_crs,
                    trace_count=metadata.trace_count,
                    line_count=1,
                    geometry=None,
                )
            )

            if segy_file.id is None:
                raise RuntimeError("Created SEG-Y file has no database ID")

            task_mgr.update_task(
                task_id,
                progress_percent=75,
                message="Processing traces and constructing line geometry...",
            )

            line_repo = SQLAlchemyLineRepository(db_session)
            shot_point_repo = SQLAlchemyShotPointRepository(db_session)
            trace_repo = SQLAlchemySeismicTraceRepository(db_session)
            persistence_service = ProcessingResultPersistenceService(
                line_repository=line_repo,
                shot_point_repository=shot_point_repo,
                trace_repository=trace_repo,
            )

            processing_service = SegyProcessingService(
                segy_reader=reader,
                trace_processor=TraceProcessor(),
                shot_point_analyzer=ShotPointAnalyzer(),
                line_builder=LineBuilder(),
                topology_analyzer=LineTopologyAnalyzer(),
                wgs84_geometry_builder=WGS84LineGeometryBuilder(),
                file_storage=file_storage,
            )

            use_case = ProcessSegyFileUseCase(
                processing_service=processing_service,
                persistence_service=persistence_service,
            )

            result = use_case.execute(
                filename=stored_path.name,
                segy_file_id=segy_file.id,
                source_crs=resolved_source_crs,
            )
            db_session.commit()

            task_mgr.update_task(
                task_id,
                progress_percent=90,
                message="Persisting geometry records to PostGIS...",
            )

            response = _processing_response(result, segy_file.id, filename)
            task_mgr.update_task(
                task_id,
                status="COMPLETED",
                progress_percent=100,
                message="Processing completed successfully",
                result=response.model_dump(),
            )
        except Exception as exc:
            db_session.rollback()
            task_mgr.update_task(task_id, status="FAILED", error=str(exc))
            try:
                file_storage.delete(stored_path)
            except Exception:
                pass


async def _upload_and_process(
    file: UploadFile,
    source_crs: str | None,
    service: SegyFileService,
    query_service: ProcessedDataQueryService,
    use_case: ProcessSegyFileUseCase,
    file_storage: FileStorage,
    session: Session | None = None,
    user_id: int | None = None,
    stored_paths: list[Path] | None = None,
    task_id: str | None = None,
) -> SegyProcessingResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An SEG-Y filename is required",
        )

    filename = Path(file.filename).name
    tid = task_id or uuid4().hex
    task_mgr = get_task_manager()
    task_mgr.create_task(tid, filename)
    task_mgr.update_task(
        tid,
        status="UPLOADING",
        progress_percent=10,
        message=f"Starting streaming upload for {filename}...",
    )

    existing = service.get_file_by_filename(filename)
    if existing is not None and existing.id is not None:
        summary = query_service.summary(existing.id)
        if summary is not None and (
            summary["processed_line_count"] > 0
            or summary["processed_trace_count"] > 0
        ):
            task_mgr.update_task(tid, status="FAILED", error="File already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A processed SEG-Y file with the same filename already exists: "
                    f"{filename}"
                ),
            )

    file_size = getattr(file, "size", 0) or 0
    try:
        stored_path = file_storage.save_stream(filename, file.file, length=file_size)
    except Exception:
        file.file.seek(0)
        file_bytes = await file.read()
        stored_path = file_storage.save(filename, file_bytes)
        file_size = len(file_bytes)

    if stored_paths is not None:
        stored_paths.append(stored_path)

    task_mgr.update_task(
        tid,
        status="PROCESSING",
        progress_percent=35,
        message="File saved, reading SEG-Y textual header & metadata...",
    )

    try:
        reader = SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        )
        resolved_local_path = file_storage.get_path(str(stored_path))
        metadata = reader.read_metadata(resolved_local_path)

        task_mgr.update_task(
            tid,
            progress_percent=55,
            message="Metadata read, cross-validating CRS...",
        )

        try:
            if source_crs:
                resolved_source_crs = validate_and_heal_source_crs(
                    source_crs, file_path=resolved_local_path
                )
            else:
                resolved_source_crs = extract_source_crs(
                    metadata, file_path=resolved_local_path
                )
        except ValueError as exc:
            task_mgr.update_task(tid, status="FAILED", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        segy_file = service.create_file(
            SegyFile(
                id=None,
                user_id=user_id,
                filename=filename,
                file_path=str(stored_path),
                file_size=file_size if file_size > 0 else 1,
                source_crs=resolved_source_crs,
                trace_count=metadata.trace_count,
                line_count=1,
                geometry=None,
            )
        )

        if segy_file.id is None:
            raise RuntimeError("Created SEG-Y file has no database ID")

        task_mgr.update_task(
            tid,
            progress_percent=75,
            message="Processing traces and constructing line geometry...",
        )

        result = use_case.execute(
            filename=stored_path.name,
            segy_file_id=segy_file.id,
            source_crs=resolved_source_crs,
        )
        if session is not None:
            session.commit()

        task_mgr.update_task(
            tid,
            progress_percent=90,
            message="Persisting geometry records to PostGIS...",
        )

        response = _processing_response(result, segy_file.id, filename)
        task_mgr.update_task(
            tid,
            status="COMPLETED",
            progress_percent=100,
            message="Processing completed successfully",
            result=response.model_dump(),
        )
        return response
    except Exception as exc:
        task_mgr.update_task(tid, status="FAILED", error=str(exc))
        file_storage.delete(stored_path)
        raise



@router.post(
    "/upload",
    response_model=SegyProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_segy_file(
    file: UploadFile = File(...),
    source_crs: str | None = Form(None),
    current_user_id: int | None = Depends(get_current_user_id),
    service: SegyFileService = Depends(get_segy_file_service),
    query_service: ProcessedDataQueryService = Depends(
        get_processed_data_query_service,
    ),
    use_case: ProcessSegyFileUseCase = Depends(
        get_process_segy_file_use_case,
    ),
    file_storage: FileStorage = Depends(get_file_storage),
    session: Session = Depends(get_db_session),
    _rl: None = Depends(upload_rate_limit(UPLOAD_SINGLE_MAX)),
) -> SegyProcessingResponse:
    return await _upload_and_process(
        file,
        source_crs,
        service,
        query_service,
        use_case,
        file_storage,
        session=session,
        user_id=current_user_id,
    )


@router.post(
    "/upload/batch",
    response_model=SegyUploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_segy_files(
    files: list[UploadFile] = File(...),
    source_crs: str | None = Form(None),
    current_user_id: int | None = Depends(get_current_user_id),
    service: SegyFileService = Depends(get_segy_file_service),
    query_service: ProcessedDataQueryService = Depends(
        get_processed_data_query_service,
    ),
    use_case: ProcessSegyFileUseCase = Depends(
        get_process_segy_file_use_case,
    ),
    file_storage: FileStorage = Depends(get_file_storage),
    session: Session = Depends(get_db_session),
    _rl: None = Depends(upload_rate_limit(UPLOAD_BATCH_MAX)),
) -> SegyUploadBatchResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one SEG-Y file is required",
        )

    results = []
    stored_paths: list[Path] = []
    try:
        for file in files:
            results.append(
                await _upload_and_process(
                    file,
                    source_crs,
                    service,
                    query_service,
                    use_case,
                    file_storage,
                    session=session,
                    user_id=current_user_id,
                    stored_paths=stored_paths,
                )
            )
    except Exception:
        # The request-scoped database dependency rolls back all records.
        for stored_path in stored_paths:
            file_storage.delete(stored_path)
        raise

    return SegyUploadBatchResponse(files=results)



@router.post(
    "",
    response_model=SegyFileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_segy_file(
    data: SegyFileCreate,
    service: SegyFileService = Depends(get_segy_file_service),
) -> SegyFileResponse:
    segy_file = SegyFile(
        id=None,
        filename=data.filename,
        file_path=data.file_path,
        file_size=data.file_size,
        source_crs=data.source_crs,
        trace_count=data.trace_count,
        line_count=data.line_count,
        geometry=data.geometry,
    )

    created = service.create_file(segy_file)

    return SegyFileResponse.model_validate(created)


@router.get(
    "",
    response_model=list[SegyFileResponse],
)
def list_segy_files(
    service: SegyFileService = Depends(get_segy_file_service),
) -> list[SegyFileResponse]:
    files = service.list_files()

    return [SegyFileResponse.model_validate(segy_file) for segy_file in files]


@router.get(
    "/{file_id}",
    response_model=SegyFileResponse,
)
def get_segy_file(
    file_id: int,
    service: SegyFileService = Depends(get_segy_file_service),
) -> SegyFileResponse:
    segy_file = service.get_file(file_id)

    if segy_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )

    return SegyFileResponse.model_validate(segy_file)


@router.get(
    "/filename/{filename}",
    response_model=SegyFileResponse,
)
def get_segy_file_by_filename(
    filename: str,
    service: SegyFileService = Depends(get_segy_file_service),
) -> SegyFileResponse:
    segy_file = service.get_file_by_filename(filename)

    if segy_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with filename='{filename}' not found",
        )

    return SegyFileResponse.model_validate(segy_file)


@router.post(
    "/{file_id}/process",
    response_model=SegyProcessingResponse,
)
def process_segy_file(
    file_id: int,
    service: SegyFileService = Depends(get_segy_file_service),
    use_case: ProcessSegyFileUseCase = Depends(
        get_process_segy_file_use_case,
    ),
) -> SegyProcessingResponse:
    segy_file = service.get_file(file_id)

    if segy_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )

    result = use_case.execute(
        filename=Path(segy_file.file_path).name,
        segy_file_id=file_id,
        source_crs=segy_file.source_crs,
    )

    return _processing_response(result, file_id, segy_file.filename)


@router.put(
    "/{file_id}",
    response_model=SegyFileResponse,
)
def update_segy_file(
    file_id: int,
    data: SegyFileUpdate,
    service: SegyFileService = Depends(get_segy_file_service),
) -> SegyFileResponse:
    existing = service.get_file(file_id)

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )

    segy_file = SegyFile(
        id=file_id,
        filename=data.filename,
        file_path=data.file_path,
        file_size=data.file_size,
        source_crs=data.source_crs,
        trace_count=data.trace_count,
        line_count=data.line_count,
        geometry=data.geometry,
        created_at=existing.created_at,
        updated_at=existing.updated_at,
    )

    updated = service.update_file(segy_file)

    return SegyFileResponse.model_validate(updated)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_segy_file(
    file_id: int,
    service: SegyFileService = Depends(get_segy_file_service),
) -> None:
    existing = service.get_file(file_id)

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )

    service.delete_file(file_id)


@router.post(
    "/batch-delete",
    response_model=SegyBatchDeleteResponse,
)
@router.delete(
    "/batch",
    response_model=SegyBatchDeleteResponse,
)
def batch_delete_segy_files(
    payload: SegyBatchDeleteRequest,
    service: SegyFileService = Depends(get_segy_file_service),
) -> SegyBatchDeleteResponse:
    deleted_ids = service.delete_files(payload.ids)
    return SegyBatchDeleteResponse(
        deleted_ids=deleted_ids,
        count=len(deleted_ids),
    )


@router.websocket("/ws/progress/{client_id}")
async def websocket_segy_progress(
    websocket: WebSocket,
    client_id: str,
):
    await ws_manager.connect(client_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id, websocket)


@router.get(
    "/tasks/{task_id}",
    response_model=SegyTaskStatusResponse,
    summary="Lấy thông tin tiến độ xử lý file SEG-Y bất đồng bộ",
)
def get_segy_task_status(
    task_id: str,
) -> SegyTaskStatusResponse:
    task_mgr = get_task_manager()
    task = task_mgr.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} not found",
        )
    return SegyTaskStatusResponse(
        task_id=task.task_id,
        filename=task.filename,
        status=task.status,
        progress_percent=task.progress_percent,
        message=task.message,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


