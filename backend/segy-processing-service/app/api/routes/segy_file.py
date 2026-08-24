from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.api.dependencies import (
    get_file_storage,
    get_processed_data_query_service,
    get_process_segy_file_use_case,
    get_segy_file_service,
)
from app.api.schemas.segy_file import (
    ProcessedPointResponse,
    SegyFileCreate,
    SegyFileResponse,
    SegyFileUpdate,
    SegyProcessingResponse,
    SegyUploadBatchResponse,
)
from app.application.use_cases.process_segy_file_use_case import (
    ProcessSegyFileUseCase,
)
from app.application.services.processed_data_query import ProcessedDataQueryService
from app.domain.models.segy_file import SegyFile
from app.infrastructure.segy.segyio_reader import SegyIOReader
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.services.segy_file_service import SegyFileService
from app.services.segy_reader import SegyReaderService
from app.services.source_crs_extractor import extract_source_crs
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


async def _upload_and_process(
    file: UploadFile,
    source_crs: str | None,
    service: SegyFileService,
    query_service: ProcessedDataQueryService,
    use_case: ProcessSegyFileUseCase,
    file_storage: LocalFileStorage,
    stored_paths: list[Path] | None = None,
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
                detail=(
                    "A processed SEG-Y file with the same filename already exists: "
                    f"{filename}"
                ),
            )

    stored_path = file_storage.save(filename, await file.read())
    if stored_paths is not None:
        stored_paths.append(stored_path)

    try:
        reader = SegyReaderService(
            reader=SegyIOReader(),
            validator=SegyValidator(),
        )
        metadata = reader.read_metadata(stored_path)
        try:
            resolved_source_crs = source_crs or extract_source_crs(metadata)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        segy_file = service.create_file(
            SegyFile(
                id=None,
                filename=filename,
                file_path=str(stored_path),
                file_size=stored_path.stat().st_size,
                source_crs=resolved_source_crs,
                trace_count=metadata.trace_count,
                line_count=1,
                geometry=None,
            )
        )

        if segy_file.id is None:
            raise RuntimeError("Created SEG-Y file has no database ID")

        result = use_case.execute(
            filename=stored_path.name,
            segy_file_id=segy_file.id,
            source_crs=resolved_source_crs,
        )
        return _processing_response(result, segy_file.id, filename)
    except Exception:
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
    service: SegyFileService = Depends(get_segy_file_service),
    query_service: ProcessedDataQueryService = Depends(
        get_processed_data_query_service,
    ),
    use_case: ProcessSegyFileUseCase = Depends(
        get_process_segy_file_use_case,
    ),
    file_storage: LocalFileStorage = Depends(get_file_storage),
) -> SegyProcessingResponse:
    return await _upload_and_process(
        file,
        source_crs,
        service,
        query_service,
        use_case,
        file_storage,
    )


@router.post(
    "/upload/batch",
    response_model=SegyUploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_segy_files(
    files: list[UploadFile] = File(...),
    source_crs: str | None = Form(None),
    service: SegyFileService = Depends(get_segy_file_service),
    query_service: ProcessedDataQueryService = Depends(
        get_processed_data_query_service,
    ),
    use_case: ProcessSegyFileUseCase = Depends(
        get_process_segy_file_use_case,
    ),
    file_storage: LocalFileStorage = Depends(get_file_storage),
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
                    stored_paths,
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
