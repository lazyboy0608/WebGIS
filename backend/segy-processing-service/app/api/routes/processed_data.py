from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.api.schemas.processed_data import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    ProcessedDataSummary,
)
from app.application.services.processed_data_query import (
    ProcessedDataQueryService,
)

router = APIRouter(
    prefix="/api/segy-files",
    tags=["Processed SEG-Y Data"],
)


def get_query_service(
    session: Session = Depends(get_db_session),
) -> ProcessedDataQueryService:
    return ProcessedDataQueryService(session)


def ensure_file_exists(
    file_id: int,
    service: ProcessedDataQueryService,
) -> None:
    if not service.file_exists(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SEG-Y file with id={file_id} not found",
        )


@router.get(
    "/{file_id}/processed/summary",
    response_model=ProcessedDataSummary,
)
@router.get(
    "/{file_id}/summary",
    response_model=ProcessedDataSummary,
)
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


@router.get(
    "/{file_id}/processed/line",
    response_model=GeoJSONFeature,
)
def get_processed_line(
    file_id: int,
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> GeoJSONFeature:
    ensure_file_exists(file_id, service)
    line = service.line(file_id)
    if line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No processed line found for SEG-Y file id={file_id}",
        )
    return GeoJSONFeature.model_validate(line)


@router.get(
    "/{file_id}/processed/lines",
    response_model=GeoJSONFeatureCollection,
)
def get_processed_lines(
    file_id: int,
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
    return GeoJSONFeatureCollection.model_validate(service.lines(file_id))


@router.get(
    "/{file_id}/processed/shot-points",
    response_model=GeoJSONFeatureCollection,
)
def get_processed_shot_points(
    file_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
    return GeoJSONFeatureCollection.model_validate(
        service.shot_points(file_id, offset=offset, limit=limit)
    )


@router.get(
    "/{file_id}/processed/traces",
    response_model=GeoJSONFeatureCollection,
)
def get_processed_traces(
    file_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    service: ProcessedDataQueryService = Depends(get_query_service),
) -> GeoJSONFeatureCollection:
    ensure_file_exists(file_id, service)
    return GeoJSONFeatureCollection.model_validate(
        service.traces(file_id, offset=offset, limit=limit)
    )
