import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.database.models.segy_file_model import SegyFileModel
from app.infrastructure.database.models.seismic_line_model import SeismicLineModel
from app.infrastructure.database.models.seismic_shot_point_model import (
    SeismicShotPointModel,
)
from app.infrastructure.database.models.seismic_trace_model import (
    SeismicTraceModel,
)


class ProcessedDataQueryService:
    """Read processed seismic data from PostgreSQL/PostGIS."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def file_exists(self, file_id: int) -> bool:
        return self._session.scalar(
            select(func.count())
            .select_from(SegyFileModel)
            .where(SegyFileModel.id == file_id)
        ) == 1

    def summary(self, file_id: int) -> dict[str, Any] | None:
        file_row = self._session.execute(
            select(
                SegyFileModel.id,
                SegyFileModel.filename,
                SegyFileModel.source_crs,
                SegyFileModel.trace_count,
                SegyFileModel.line_count,
            ).where(SegyFileModel.id == file_id)
        ).mappings().one_or_none()

        if file_row is None:
            return None

        line_count = self._count(SeismicLineModel, file_id)
        shot_point_count = self._count(SeismicShotPointModel, file_id)
        trace_count = self._count(SeismicTraceModel, file_id)

        return {
            **dict(file_row),
            "processed_line_count": line_count,
            "processed_shot_point_count": shot_point_count,
            "processed_trace_count": trace_count,
        }

    def line(self, file_id: int) -> dict[str, Any] | None:
        rows = self._line_rows(file_id, limit=1)
        if not rows:
            return None
        return self._line_feature(rows[0])

    def lines(self, file_id: int) -> dict[str, Any]:
        return self._feature_collection(
            self._line_feature(row)
            for row in self._line_rows(file_id)
        )

    def _line_rows(self, file_id: int, limit: int | None = None):
        statement = (
            select(
                SeismicLineModel.id,
                SeismicLineModel.line_id,
                SeismicLineModel.point_count,
                func.ST_AsGeoJSON(SeismicLineModel.geometry).label("geometry"),
                func.ST_SRID(SeismicLineModel.geometry).label("srid"),
            )
            .where(SeismicLineModel.segy_file_id == file_id)
            .order_by(SeismicLineModel.id)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return self._session.execute(statement).mappings().all()

    @staticmethod
    def _line_feature(row) -> dict[str, Any]:
        return ProcessedDataQueryService._feature(
            geometry=row["geometry"],
            properties={
                "id": row["id"],
                "line_id": row["line_id"],
                "point_count": row["point_count"],
                "srid": row["srid"],
            },
        )

    def shot_points(
        self,
        file_id: int,
        offset: int = 0,
        limit: int = 1000,
    ) -> dict[str, Any]:
        rows = self._session.execute(
            select(
                SeismicShotPointModel.id,
                SeismicShotPointModel.shot_point_number,
                SeismicShotPointModel.seismic_line_id,
                SeismicShotPointModel.trace_count,
                func.ST_AsGeoJSON(SeismicShotPointModel.geometry).label(
                    "geometry"
                ),
                func.ST_SRID(SeismicShotPointModel.geometry).label("srid"),
            )
            .where(SeismicShotPointModel.segy_file_id == file_id)
            .order_by(SeismicShotPointModel.shot_point_number)
            .offset(offset)
            .limit(limit)
        ).mappings().all()

        return self._feature_collection(
            self._feature(
                geometry=row["geometry"],
                properties={
                    "id": row["id"],
                    "shot_point": row["shot_point_number"],
                    "seismic_line_id": row["seismic_line_id"],
                    "trace_count": row["trace_count"],
                    "srid": row["srid"],
                },
            )
            for row in rows
        )

    def traces(
        self,
        file_id: int,
        offset: int = 0,
        limit: int = 1000,
    ) -> dict[str, Any]:
        rows = self._session.execute(
            select(
                SeismicTraceModel.id,
                SeismicTraceModel.trace_index,
                SeismicTraceModel.seismic_line_id,
                SeismicTraceModel.shot_point_id,
                func.ST_AsGeoJSON(SeismicTraceModel.geometry).label("geometry"),
                func.ST_SRID(SeismicTraceModel.geometry).label("srid"),
            )
            .where(SeismicTraceModel.segy_file_id == file_id)
            .order_by(SeismicTraceModel.trace_index)
            .offset(offset)
            .limit(limit)
        ).mappings().all()

        return self._feature_collection(
            self._feature(
                geometry=row["geometry"],
                properties={
                    "id": row["id"],
                    "trace_index": row["trace_index"],
                    "seismic_line_id": row["seismic_line_id"],
                    "shot_point_id": row["shot_point_id"],
                    "srid": row["srid"],
                },
            )
            for row in rows
        )

    def _count(self, model: Any, file_id: int) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(model).where(
                    model.segy_file_id == file_id
                )
            )
        )

    @staticmethod
    def _feature(geometry: str | None, properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "Feature",
            "geometry": None if geometry is None else json.loads(geometry),
            "properties": properties,
        }

    @staticmethod
    def _feature_collection(features: Any) -> dict[str, Any]:
        return {"type": "FeatureCollection", "features": list(features)}
