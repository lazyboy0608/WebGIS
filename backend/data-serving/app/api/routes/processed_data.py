from typing import Any

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.processed_data import (
    BatchExportCsvResponse,
    BatchExportRequest,
    DownloadUrlResponse,
    ExportCsvResponse,
    FileListResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    ProcessedDataSummary,
)
from app.config import settings
from app.core.rate_limiter import user_rate_limit
from app.database import get_db_session
from app.models import UserModel
from app.services.export_service import ExportService
from app.services.processed_data_query import ProcessedDataQueryService

router = APIRouter(prefix="/api/segy-files", tags=["Processed Data"])


def get_query_service(
    session: Session = Depends(get_db_session),
) -> ProcessedDataQueryService:
    return ProcessedDataQueryService(session)


def get_export_service(
    session: Session = Depends(get_db_session),
) -> ExportService:
    return ExportService(session)


def _user_id_filter(current_user: UserModel) -> int | None:

    """Return None (no filter) for admins, or user's own id for regular users."""
    return None if current_user.role == "admin" else current_user.id


def ensure_file_accessible(
    file_id: int,
    service: ProcessedDataQueryService,
    user_id: int | None,
) -> None:
    if not service.file_exists(file_id, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )


@router.get("", response_model=FileListResponse)
def list_files(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> FileListResponse:
    user_id = _user_id_filter(current_user)
    payload = service.list_files(offset=offset, limit=limit, user_id=user_id)
    return FileListResponse.model_validate(payload)


@router.get("/{file_id}/processed/summary", response_model=ProcessedDataSummary)
def get_processed_summary(
    file_id: int,
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> ProcessedDataSummary:
    user_id = _user_id_filter(current_user)
    summary = service.summary(file_id, user_id=user_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )
    return ProcessedDataSummary.model_validate(summary)


@router.get("/{file_id}/processed/line", response_model=GeoJSONFeature)
def get_processed_line(
    file_id: int,
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> GeoJSONFeature:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, service, user_id)
    line = service.line(file_id)
    if line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No processed line found for SEG-Y file id={file_id}. Use /processed/lines instead.",
        )
    return GeoJSONFeature.model_validate(line)


@router.get("/{file_id}/processed/lines", response_model=GeoJSONFeatureCollection)
def get_processed_lines(
    file_id: int,
    line_id: int | None = Query(default=None, ge=1),
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> GeoJSONFeatureCollection:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, service, user_id)
    try:
        payload = service.lines(file_id, line_id=line_id, bbox=bbox, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GeoJSONFeatureCollection.model_validate(payload)


@router.get("/{file_id}/processed/shot-points", response_model=GeoJSONFeatureCollection)
def get_processed_shot_points(
    file_id: int,
    shot_point_number: int | None = Query(default=None, ge=0),
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> GeoJSONFeatureCollection:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, service, user_id)
    try:
        payload = service.shot_points(
            file_id,
            shot_point_number=shot_point_number,
            bbox=bbox,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GeoJSONFeatureCollection.model_validate(payload)


@router.get("/{file_id}/processed/traces", response_model=GeoJSONFeatureCollection)
def get_processed_traces(
    file_id: int,
    line_id: int | None = Query(default=None, ge=1),
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
) -> GeoJSONFeatureCollection:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, service, user_id)
    try:
        payload = service.traces(file_id, line_id=line_id, bbox=bbox, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GeoJSONFeatureCollection.model_validate(payload)


@router.post("/{file_id}/processed/lines/clip", response_model=GeoJSONFeatureCollection)
def clip_processed_lines(
    file_id: int,
    polygon: dict[str, Any],
    line_id: int | None = Query(default=None, ge=1),
    service: ProcessedDataQueryService = Depends(get_query_service),
    current_user: UserModel = Depends(get_current_user),
    _rl: None = Depends(user_rate_limit(settings.rate_limit_clip, settings.rate_limit_window_seconds)),
) -> GeoJSONFeatureCollection:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, service, user_id)
    try:
        payload = service.clip_lines_by_polygon(file_id, polygon_geojson=polygon, line_id=line_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GeoJSONFeatureCollection.model_validate(payload)


@router.get("/{file_id}/download-url", response_model=DownloadUrlResponse)
def get_raw_file_download_url(
    file_id: int,
    query_service: ProcessedDataQueryService = Depends(get_query_service),
    export_service: ExportService = Depends(get_export_service),
    current_user: UserModel = Depends(get_current_user),
) -> DownloadUrlResponse:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, query_service, user_id)
    try:
        res = export_service.get_raw_file_download_url(file_id)
        return DownloadUrlResponse.model_validate(res)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {exc}",
        ) from exc


@router.post("/export/csv/batch", response_model=BatchExportCsvResponse)
def export_batch_csv(
    body: BatchExportRequest,
    query_service: ProcessedDataQueryService = Depends(get_query_service),
    export_service: ExportService = Depends(get_export_service),
    current_user: UserModel = Depends(get_current_user),
) -> BatchExportCsvResponse:
    """Export one CSV per selected SEG-Y file. Each CSV is saved to MinIO
    and a presigned download URL is returned (1 SEG-Y = 1 CSV)."""
    user_id = _user_id_filter(current_user)
    # Validate all requested file IDs are accessible for this user
    for file_id in body.ids:
        ensure_file_accessible(file_id, query_service, user_id)
    try:
        raw_results = export_service.export_batch_csv(body.ids)
        results = [ExportCsvResponse.model_validate(r) for r in raw_results]
        return BatchExportCsvResponse(results=results, total=len(results))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV batch: {exc}",
        ) from exc


@router.post("/{file_id}/export/csv", response_model=ExportCsvResponse)
def export_traces_csv(
    file_id: int,
    query_service: ProcessedDataQueryService = Depends(get_query_service),
    export_service: ExportService = Depends(get_export_service),
    current_user: UserModel = Depends(get_current_user),
) -> ExportCsvResponse:
    user_id = _user_id_filter(current_user)
    ensure_file_accessible(file_id, query_service, user_id)
    try:
        res = export_service.export_traces_csv(file_id)
        return ExportCsvResponse.model_validate(res)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {exc}",
        ) from exc
