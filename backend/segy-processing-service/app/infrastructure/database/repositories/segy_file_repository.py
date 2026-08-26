from typing import Optional

from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiLineString, mapping
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.interfaces.repositories.segy_file_repository import (
    SegyFileRepository,
)
from app.domain.models.coordinate import Coordinate
from app.domain.models.segy_file import SegyFile
from app.infrastructure.database.models.segy_file_model import (
    SegyFileModel,
)


class SQLAlchemySegyFileRepository(SegyFileRepository):
    """SQLAlchemy implementation of SegyFileRepository."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, segy_file: SegyFile) -> SegyFile:
        model = SegyFileModel(
            user_id=segy_file.user_id,
            filename=segy_file.filename,
            file_path=segy_file.file_path,
            file_size=segy_file.file_size,
            source_crs=segy_file.source_crs,
            trace_count=segy_file.trace_count,
            line_count=segy_file.line_count,
            geometry=segy_file.geometry,
        )

        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)

        return self._to_domain(model)

    def get_by_id(self, file_id: int) -> Optional[SegyFile]:
        model = self.session.get(SegyFileModel, file_id)

        if model is None:
            return None

        return self._to_domain(model)

    def get_by_filename(
        self,
        filename: str,
    ) -> Optional[SegyFile]:

        stmt = select(SegyFileModel).where(SegyFileModel.filename == filename)

        model = self.session.scalar(stmt)

        if model is None:
            return None

        return self._to_domain(model)

    def list_all(self) -> list[SegyFile]:
        stmt = select(SegyFileModel)

        models = self.session.scalars(stmt).all()

        return [self._to_domain(model) for model in models]

    def update(self, segy_file: SegyFile) -> SegyFile:
        model = self.session.get(
            SegyFileModel,
            segy_file.id,
        )

        if model is None:
            raise ValueError(f"SEG-Y file with id={segy_file.id} not found")

        model.filename = segy_file.filename
        model.file_path = segy_file.file_path
        model.file_size = segy_file.file_size
        model.source_crs = segy_file.source_crs
        model.trace_count = segy_file.trace_count
        model.line_count = segy_file.line_count
        model.geometry = segy_file.geometry

        self.session.flush()
        self.session.refresh(model)

        return self._to_domain(model)

    def delete(self, file_id: int) -> None:
        model = self.session.get(
            SegyFileModel,
            file_id,
        )

        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def intersects_polygon(self, polygon):
        stmt = select(SegyFileModel).where(
            SegyFileModel.geometry.ST_Intersects(polygon)
        )

        models = self.session.scalars(stmt).all()

        return [self._to_domain(model) for model in models]

    def update_geometry(
        self,
        file_id: int,
        coordinates: list[list[Coordinate]],
    ) -> SegyFile:
        if not coordinates or any(len(line) < 2 for line in coordinates):
            raise ValueError(
                "A SEG-Y file geometry must contain at least two coordinates."
            )

        model = self.session.get(SegyFileModel, file_id)
        if model is None:
            raise ValueError(f"SEG-Y file with id={file_id} not found")

        lines = [
            [(coordinate.x, coordinate.y) for coordinate in line]
            for line in coordinates
        ]
        geometry = MultiLineString(lines)
        model.geometry = from_shape(geometry, srid=4326)
        model.line_count = len(lines)

        self.session.flush()
        self.session.refresh(model)
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: SegyFileModel) -> SegyFile:
        geometry = model.geometry
        if isinstance(geometry, (WKBElement, WKTElement)):
            geometry = mapping(to_shape(geometry))

        return SegyFile(
            id=model.id,
            user_id=model.user_id,
            filename=model.filename,
            file_path=model.file_path,
            file_size=model.file_size,
            source_crs=model.source_crs,
            trace_count=model.trace_count,
            line_count=model.line_count,
            geometry=geometry,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
