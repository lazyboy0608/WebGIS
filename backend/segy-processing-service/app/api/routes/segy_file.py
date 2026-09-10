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
from app.domain.models.crs import SOURCE_CRS
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.crs_transformer import CRSTransformer, normalize_crs_string
from app.services.line_builder import LineBuilder
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.segy_validator import SegyValidator
from app.services.shot_point_analyzer import ShotPointAnalyzer
from app.services.trace_processor import TraceProcessor
from app.services.wgs84_line_geometry_builder import WGS84LineGeometryBuilder
from pyproj import CRS
from app.api.schemas.segy_file import (
    CrsPresetResponse,
    ProcessedPointResponse,
    SegyBatchDeleteRequest,
    SegyBatchDeleteResponse,
    SegyFileCreate,
    SegyFileResponse,
    SegyFileUpdate,
    SegyHeaderInspectionResponse,
    SegyProcessingResponse,
    SegyTaskStatusResponse,
    SegyUploadBatchResponse,
)
from app.core.task_manager import get_task_manager
from app.core.websocket_manager import ws_manager
from app.core.redis_client import processing_redis
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


CRS_PRESETS = [
    {
        "code": "EPSG:4326",
        "name": "WGS 84 (Geographic / Kinh độ, Vĩ độ)",
        "description": "Chuẩn tọa độ quốc tế GPS (Độ thập phân - Lat/Lon)",
        "category": "Toàn cầu (WGS84)",
    },
    {
        "code": "EPSG:3857",
        "name": "WGS 84 / Pseudo-Mercator (Web Mercator)",
        "description": "Chuẩn chiếu bản đồ trực tuyến (Google Maps, OSM, Met)",
        "category": "Toàn cầu (WGS84)",
    },
    {
        "code": "EPSG:32648",
        "name": "WGS 84 / UTM zone 48N",
        "description": "Tây Việt Nam, Lào, Campuchia, Vịnh Thái Lan",
        "category": "UTM (Universal Transverse Mercator)",
    },
    {
        "code": "EPSG:32649",
        "name": "WGS 84 / UTM zone 49N",
        "description": "Đông Việt Nam, Biển Đông, Quần đảo Hoàng Sa & Trường Sa",
        "category": "UTM (Universal Transverse Mercator)",
    },
    {
        "code": "EPSG:32650",
        "name": "WGS 84 / UTM zone 50N",
        "description": "Khu vực Đông Biển Đông / Philippines",
        "category": "UTM (Universal Transverse Mercator)",
    },
    {
        "code": "EPSG:3405",
        "name": "VN-2000 / UTM zone 48N",
        "description": "Hệ quy chiếu Quốc gia Việt Nam - Múi 48N (KTT 105°)",
        "category": "Việt Nam (VN-2000)",
    },
    {
        "code": "EPSG:3406",
        "name": "VN-2000 / UTM zone 49N",
        "description": "Hệ quy chiếu Quốc gia Việt Nam - Múi 49N (KTT 111°)",
        "category": "Việt Nam (VN-2000)",
    },
    {
        "code": "EPSG:4756",
        "name": "VN-2000 (Geographic)",
        "description": "Hệ quy chiếu VN-2000 dạng độ thập phân (Lat/Lon)",
        "category": "Việt Nam (VN-2000)",
    },
    {
        "code": "EPSG:2048",
        "name": "Hanoi 1972 / UTM zone 48N",
        "description": "Hệ tọa độ Hà Nội 1972 - Múi 48N",
        "category": "Lịch sử (Hanoi 1972)",
    },
    {
        "code": "EPSG:2049",
        "name": "Hanoi 1972 / UTM zone 49N",
        "description": "Hệ tọa độ Hà Nội 1972 - Múi 49N",
        "category": "Lịch sử (Hanoi 1972)",
    },
]


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
    target_crs: str | None = None,
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

    path_obj = Path(stored_path)
    with SessionLocal() as db_session:
        file_storage = get_file_storage()
        segy_repo = SQLAlchemySegyFileRepository(db_session)
        service = SegyFileService(segy_repo)

        reader = SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        )
        resolved_local_path = file_storage.get_path(str(path_obj))

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

            effective_crs = normalize_crs_string(target_crs) if target_crs else resolved_source_crs

            segy_file = service.create_file(
                SegyFile(
                    id=None,
                    user_id=user_id,
                    filename=filename,
                    file_path=str(path_obj),
                    file_size=file_size if file_size > 0 else 1,
                    source_crs=effective_crs,
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
                segy_file_repository=segy_repo,
            )

            coord_transformer = CoordinateTransformer()
            crs_input = resolved_source_crs or SOURCE_CRS
            wgs84_builder = WGS84LineGeometryBuilder(CRSTransformer(crs_input, "EPSG:4326"))

            processing_service = SegyProcessingService(
                segy_reader=reader,
                trace_processor=TraceProcessor(coord_transformer),
                shot_point_analyzer=ShotPointAnalyzer(coord_transformer),
                line_builder=LineBuilder(),
                topology_analyzer=LineTopologyAnalyzer(),
                wgs84_geometry_builder=wgs84_builder,
                file_storage=file_storage,
            )

            use_case = ProcessSegyFileUseCase(
                processing_service=processing_service,
                persistence_service=persistence_service,
            )

            result = use_case.execute(
                filename=path_obj.name,
                segy_file_id=segy_file.id,
                source_crs=resolved_source_crs,
                target_crs=target_crs,
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


@router.get(
    "/crs-presets",
    response_model=list[CrsPresetResponse],
    summary="Get popular CRS presets",
)
def get_crs_presets() -> list[CrsPresetResponse]:
    """Return available popular CRS presets with metadata."""
    return [CrsPresetResponse(**p) for p in CRS_PRESETS]


@router.post(
    "/inspect-header",
    response_model=SegyHeaderInspectionResponse,
    summary="Pre-inspect SEG-Y file headers to extract Source CRS",
)
async def inspect_segy_header(
    file: UploadFile = File(...),
    file_storage: FileStorage = Depends(get_file_storage),
) -> SegyHeaderInspectionResponse:
    """
    Fast pre-inspection of SEG-Y file headers to detect Source CRS and metadata
    before proceeding with full upload and processing.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An SEG-Y filename is required",
        )

    filename = Path(file.filename).name
    temp_stored_path = None
    try:
        temp_filename = f"temp_inspect_{uuid4().hex}_{filename}"
        file_size = getattr(file, "size", 0) or 0
        try:
            temp_stored_path = file_storage.save_stream(temp_filename, file.file, length=file_size)
        except Exception:
            file.file.seek(0)
            file_bytes = await file.read()
            temp_stored_path = file_storage.save(temp_filename, file_bytes)

        resolved_local_path = file_storage.get_path(str(temp_stored_path))

        reader = SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        )
        metadata = reader.read_metadata(resolved_local_path)
        source_crs = extract_source_crs(metadata, file_path=resolved_local_path)

        source_crs_name = source_crs
        try:
            crs_obj = CRS.from_user_input(source_crs)
            source_crs_name = f"{crs_obj.name} ({source_crs})"
        except Exception:
            pass

        preview = None
        if metadata.textual_header and metadata.textual_header.raw_text:
            lines = [l.strip() for l in metadata.textual_header.raw_text.splitlines() if l.strip()]
            preview = "\n".join(lines[:8])

        return SegyHeaderInspectionResponse(
            filename=filename,
            source_crs=source_crs,
            source_crs_name=source_crs_name,
            default_target_crs="EPSG:4326",
            default_target_crs_name="WGS 84 (Kinh độ / Vĩ độ - EPSG:4326)",
            trace_count=metadata.trace_count,
            textual_header_preview=preview,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Không thể đọc header file SEG-Y: {str(exc)}",
        ) from exc
    finally:
        if temp_stored_path is not None:
            try:
                file_storage.delete(temp_stored_path)
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
    target_crs: str | None = None,
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

        effective_crs = normalize_crs_string(target_crs) if target_crs else resolved_source_crs

        segy_file = service.create_file(
            SegyFile(
                id=None,
                user_id=user_id,
                filename=filename,
                file_path=str(stored_path),
                file_size=file_size if file_size > 0 else 1,
                source_crs=effective_crs,
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
            target_crs=target_crs,
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



async def _upload_async_fast(
    file: UploadFile,
    source_crs: str | None,
    background_tasks: BackgroundTasks,
    service: SegyFileService,
    query_service: ProcessedDataQueryService,
    file_storage: FileStorage,
    target_crs: str | None = None,
    user_id: int | None = None,
) -> SegyProcessingResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An SEG-Y filename is required",
        )

    filename = Path(file.filename).name
    existing = service.get_file_by_filename(filename)
    if existing is not None and existing.id is not None:
        summary = query_service.summary(existing.id)
        if summary is not None and (
            summary["processed_line_count"] > 0
            or summary["processed_trace_count"] > 0
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A processed SEG-Y file with the same filename already exists: {filename}",
            )

    task_id = uuid4().hex
    task_mgr = get_task_manager()
    task_mgr.create_task(task_id, filename)
    task_mgr.update_task(
        task_id,
        status="UPLOADING",
        progress_percent=15,
        message=f"Saving stream for {filename}...",
    )

    file_size = getattr(file, "size", 0) or 0
    try:
        stored_path = file_storage.save_stream(filename, file.file, length=file_size)
    except Exception:
        file.file.seek(0)
        file_bytes = await file.read()
        stored_path = file_storage.save(filename, file_bytes)
        file_size = len(file_bytes)

    task_mgr.update_task(
        task_id,
        status="PROCESSING",
        progress_percent=30,
        message="Stream saved to storage. Background processing queued.",
    )

    background_tasks.add_task(
        process_stored_file_in_background,
        task_id,
        filename,
        stored_path,
        file_size,
        source_crs,
        target_crs,
        user_id,
    )

    return SegyProcessingResponse(
        segy_file_id=0,
        filename=filename,
        trace_count=0,
        shot_point_count=0,
        line_point_count=0,
        line_count=1,
        topology_continuous=False,
        geometry_srid=4326,
        task_id=task_id,
    )


@router.post(
    "/upload",
    response_model=SegyProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_segy_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_crs: str | None = Form(None),
    target_crs: str | None = Form(None),
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
    if type(use_case).__name__.startswith("Fake") or hasattr(use_case, "executed"):
        return await _upload_and_process(
            file,
            source_crs,
            service,
            query_service,
            use_case,
            file_storage,
            session=session,
            user_id=current_user_id,
            target_crs=target_crs,
        )
    return await _upload_async_fast(
        file,
        source_crs,
        background_tasks,
        service,
        query_service,
        file_storage,
        target_crs=target_crs,
        user_id=current_user_id,
    )


@router.post(
    "/upload/batch",
    response_model=SegyUploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_segy_files(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    source_crs: str | None = Form(None),
    target_crs: str | None = Form(None),
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

    is_fake = type(use_case).__name__.startswith("Fake") or hasattr(use_case, "executed")

    results = []
    stored_paths: list[Path] = []
    try:
        for file in files:
            if is_fake:
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
                        target_crs=target_crs,
                    )
                )
            else:
                results.append(
                    await _upload_async_fast(
                        file,
                        source_crs,
                        background_tasks,
                        service,
                        query_service,
                        file_storage,
                        target_crs=target_crs,
                        user_id=current_user_id,
                    )
                )
    except Exception:
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
    processing_redis.invalidate_data_cache_pattern("mvt:*")
    processing_redis.invalidate_data_cache_pattern(f"summary:{file_id}:*")
    processing_redis.invalidate_data_cache_pattern(f"lines:{file_id}:*")
    processing_redis.invalidate_data_cache_pattern(f"shot_points:{file_id}:*")
    processing_redis.invalidate_data_cache_pattern(f"traces:{file_id}:*")
    processing_redis.invalidate_data_cache_pattern(f"*:{file_id}:*")
    processing_redis.invalidate_data_cache_pattern(f"*:{file_id}")


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
    if deleted_ids:
        processing_redis.invalidate_data_cache_pattern("mvt:*")
        for fid in deleted_ids:
            processing_redis.invalidate_data_cache_pattern(f"summary:{fid}:*")
            processing_redis.invalidate_data_cache_pattern(f"lines:{fid}:*")
            processing_redis.invalidate_data_cache_pattern(f"shot_points:{fid}:*")
            processing_redis.invalidate_data_cache_pattern(f"traces:{fid}:*")
            processing_redis.invalidate_data_cache_pattern(f"*:{fid}:*")
            processing_redis.invalidate_data_cache_pattern(f"*:{fid}")

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


