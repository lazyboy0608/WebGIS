from geoalchemy2.shape import from_shape
from shapely.geometry import LineString as ShapelyLineString
from sqlalchemy.orm import Session

from app.domain.interfaces.repositories.line_repository import LineRepository
from app.domain.models.seismic_line import SeismicLine
from app.infrastructure.database.models.seismic_line_model import (
    SeismicLineModel,
)


class SQLAlchemyLineRepository(LineRepository):
    """SQLAlchemy implementation for seismic line persistence."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def save_line(
        self,
        line: SeismicLine,
        segy_file_id: int,
    ) -> SeismicLine:

        if not line.coordinates:
            raise ValueError("Cannot persist a seismic line without coordinates.")

        if len(line.coordinates) < 2:
            raise ValueError("A seismic line must contain at least two coordinates.")

        geometry = ShapelyLineString(
            [(coordinate.x, coordinate.y) for coordinate in line.coordinates]
        )

        model = SeismicLineModel(
            line_id=line.line_id,
            segy_file_id=segy_file_id,
            geometry=from_shape(
                geometry,
                srid=4326,
            ),
            point_count=len(line.coordinates),
        )

        self.session.add(model)
        self.session.flush()

        return SeismicLine(
            line_id=model.line_id,
            coordinates=line.coordinates,
            id=model.id,
        )
