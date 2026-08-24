from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.domain.interfaces.repositories.shot_point_repository import (
    ShotPointRepository,
)
from app.domain.models.seismic_shot_point import (
    SeismicShotPoint,
)
from app.infrastructure.database.models.seismic_shot_point_model import (
    SeismicShotPointModel,
)


class SQLAlchemyShotPointRepository(ShotPointRepository):
    """SQLAlchemy implementation for seismic shot point persistence."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def save_shot_point(
        self,
        shot_point: SeismicShotPoint,
        segy_file_id: int,
        seismic_line_id: int | None = None,
    ) -> SeismicShotPoint:

        if not shot_point.coordinates:
            raise ValueError("Cannot persist a shot point without coordinates.")

        coordinate = shot_point.coordinates[0]

        geometry = Point(
            coordinate.x,
            coordinate.y,
        )

        model = SeismicShotPointModel(
            shot_point_number=shot_point.number,
            segy_file_id=segy_file_id,
            seismic_line_id=seismic_line_id,
            geometry=from_shape(
                geometry,
                srid=4326,
            ),
            trace_count=len(shot_point.trace_indices),
        )

        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)

        return SeismicShotPoint(
            id=model.id,
            number=model.shot_point_number,
            trace_indices=shot_point.trace_indices,
            coordinates=shot_point.coordinates,
        )
