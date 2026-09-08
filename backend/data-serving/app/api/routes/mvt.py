from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.services.mvt_service import MVTService

router = APIRouter(
    prefix="/api/segy-files",
    tags=["Vector Tiles (MVT)"],
)


def get_mvt_service(
    session: Session = Depends(get_db_session),
) -> MVTService:
    return MVTService(session)


@router.get("/mvt/{z}/{x}/{y}.pbf")
def get_all_vector_tile(
    z: int,
    x: int,
    y: int,
    file_ids: str | None = Query(None, description="Comma separated file IDs, e.g. '1,2,3'"),
    layers: str | None = Query(None, description="Comma separated layers: 'lines,shot_points,traces'"),
    mvt_service: MVTService = Depends(get_mvt_service),
) -> Response:
    parsed_file_ids = [int(f.strip()) for f in file_ids.split(",") if f.strip().isdigit()] if file_ids else None
    parsed_layers = [l.strip() for l in layers.split(",") if l.strip()] if layers else None

    tile_bytes = mvt_service.generate_tile(
        z=z,
        x=x,
        y=y,
        file_ids=parsed_file_ids,
        layers=parsed_layers,
    )

    return Response(
        content=tile_bytes,
        media_type="application/x-protobuf",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{file_id}/mvt/{z}/{x}/{y}.pbf")
def get_file_vector_tile(
    file_id: int,
    z: int,
    x: int,
    y: int,
    layers: str | None = Query(None, description="Comma separated layers: 'lines,shot_points,traces'"),
    mvt_service: MVTService = Depends(get_mvt_service),
) -> Response:
    parsed_layers = [l.strip() for l in layers.split(",") if l.strip()] if layers else None

    tile_bytes = mvt_service.generate_tile(
        z=z,
        x=x,
        y=y,
        file_id=file_id,
        layers=parsed_layers,
    )

    return Response(
        content=tile_bytes,
        media_type="application/x-protobuf",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )
