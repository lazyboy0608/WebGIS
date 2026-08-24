from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.processed_data import (
    FileListResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    ProcessedDataSummary,
)
from app.database import get_db_session
from app.services.processed_data_query import ProcessedDataQueryService

router = APIRouter(prefix="/api/segy-files", tags=["Processed Data"])


def get_query_service(
    session: Session = Depends(get_db_session),
) -> ProcessedDataQueryService:
    return ProcessedDataQueryService(session)


def ensure_file_exists(file_id: int, service: ProcessedDataQueryService) -> None:
    if not service.file_exists(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )


@router.get("", response_model=FileListResponse)
def list_files(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> FileListResponse:
    payload = service.list_files(offset=offset, limit=limit)
    return FileListResponse.model_validate(payload)


@router.get("/{file_id}/processed/summary", response_model=ProcessedDataSummary)
def get_processed_summary(
    file_id: int,
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> ProcessedDataSummary:
    summary = service.summary(file_id)
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
) -> GeoJSONFeature:
    ensure_file_exists(file_id, service)
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
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
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
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
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
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
    try:
        payload = service.traces(file_id, line_id=line_id, bbox=bbox, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return GeoJSONFeatureCollection.model_validate(payload)
