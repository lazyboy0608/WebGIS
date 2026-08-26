from __future__ import annotations

import time
from typing import Any

from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.geojson import feature_collection, geometry_to_geojson


class ProcessedDataQueryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl_seconds = 60

    def _cached(self, key: str, loader: Any) -> Any:
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < self._cache_ttl_seconds:
            return cached[1]

        value = loader()
        self._cache[key] = (now, value)
        return value

    def file_exists(self, file_id: int, user_id: int | None = None) -> bool:
        from app.models import SegyFileModel

        stmt = select(SegyFileModel.id).where(SegyFileModel.id == file_id)
        if user_id is not None:
            stmt = stmt.where(
                (SegyFileModel.user_id == user_id) | (SegyFileModel.user_id.is_(None))
            )
        return self.session.execute(stmt).first() is not None

    def list_files(self, offset: int = 0, limit: int = 50, user_id: int | None = None) -> dict[str, Any]:
        from app.models import SegyFileModel, SeismicLineModel, SeismicShotPointModel, SeismicTraceModel

        count_stmt = select(func.count()).select_from(SegyFileModel)
        select_stmt = select(
            SegyFileModel.id,
            SegyFileModel.filename,
            SegyFileModel.source_crs,
            SegyFileModel.trace_count,
            SegyFileModel.line_count,
        ).order_by(SegyFileModel.id).offset(offset).limit(limit)

        if user_id is not None:
            count_stmt = count_stmt.where(SegyFileModel.user_id == user_id)
            select_stmt = select_stmt.where(SegyFileModel.user_id == user_id)

        total = self.session.execute(count_stmt).scalar_one()
        rows = self.session.execute(select_stmt).all()

        items: list[dict[str, Any]] = []
        for row in rows:
            file_id, filename, source_crs, trace_count, line_count = row
            processed_line_count = self.session.execute(
                select(func.count()).select_from(SeismicLineModel).where(SeismicLineModel.segy_file_id == file_id)
            ).scalar_one()
            processed_shot_point_count = self.session.execute(
                select(func.count()).select_from(SeismicShotPointModel).where(SeismicShotPointModel.segy_file_id == file_id)
            ).scalar_one()
            processed_trace_count = self.session.execute(
                select(func.count()).select_from(SeismicTraceModel).where(SeismicTraceModel.segy_file_id == file_id)
            ).scalar_one()

            items.append(
                {
                    "id": file_id,
                    "filename": filename,
                    "source_crs": source_crs,
                    "trace_count": trace_count,
                    "line_count": line_count,
                    "processed_line_count": processed_line_count,
                    "processed_shot_point_count": processed_shot_point_count,
                    "processed_trace_count": processed_trace_count,
                    "has_processed_data": processed_line_count > 0 or processed_trace_count > 0,
                }
            )

        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def summary(self, file_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        from app.models import SegyFileModel, SeismicLineModel, SeismicShotPointModel, SeismicTraceModel

        def load() -> dict[str, Any] | None:
            stmt = select(
                SegyFileModel.id,
                SegyFileModel.filename,
                SegyFileModel.source_crs,
                SegyFileModel.trace_count,
                SegyFileModel.line_count,
            ).where(SegyFileModel.id == file_id)
            if user_id is not None:
                stmt = stmt.where(
                    (SegyFileModel.user_id == user_id) | (SegyFileModel.user_id.is_(None))
                )
            row = self.session.execute(stmt).first()

            if row is None:
                return None

            processed_line_count = self.session.execute(
                select(func.count()).select_from(SeismicLineModel).where(SeismicLineModel.segy_file_id == file_id)
            ).scalar_one()
            processed_shot_point_count = self.session.execute(
                select(func.count()).select_from(SeismicShotPointModel).where(SeismicShotPointModel.segy_file_id == file_id)
            ).scalar_one()
            processed_trace_count = self.session.execute(
                select(func.count()).select_from(SeismicTraceModel).where(SeismicTraceModel.segy_file_id == file_id)
            ).scalar_one()

            return {
                "id": row[0],
                "filename": row[1],
                "source_crs": row[2],
                "trace_count": row[3],
                "line_count": row[4],
                "processed_line_count": processed_line_count,
                "processed_shot_point_count": processed_shot_point_count,
                "processed_trace_count": processed_trace_count,
            }

        return self._cached(f"summary:{file_id}", load)

    @staticmethod
    def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
        if bbox is None:
            return None

        try:
            values = [float(v) for v in bbox.split(",")]
        except ValueError as exc:  # pragma: no cover
            raise ValueError("bbox must be 'minLon,minLat,maxLon,maxLat'") from exc

        if len(values) != 4:
            raise ValueError("bbox must contain exactly 4 comma-separated values")

        min_lon, min_lat, max_lon, max_lat = values
        return min_lon, min_lat, max_lon, max_lat

    @staticmethod
    def _bbox_polygon(bbox: str | None):
        bounds = ProcessedDataQueryService._parse_bbox(bbox)
        if bounds is None:
            return None
        min_lon, min_lat, max_lon, max_lat = bounds
        polygon_wkt = (
            f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, "
            f"{min_lon} {max_lat}, {min_lon} {min_lat}))"
        )
        return WKTElement(polygon_wkt, srid=4326)

    def line(self, file_id: int) -> dict[str, Any] | None:
        from app.models import SeismicLineModel, SeismicShotPointModel, SeismicTraceModel

        row = self.session.execute(
            select(
                SeismicLineModel.id,
                SeismicLineModel.line_id,
                SeismicLineModel.point_count,
                SeismicLineModel.geometry,
                select(func.count(SeismicTraceModel.id))
                .where(SeismicTraceModel.seismic_line_id == SeismicLineModel.id)
                .scalar_subquery()
                .label("trace_count"),
                select(func.count(SeismicShotPointModel.id))
                .where(SeismicShotPointModel.seismic_line_id == SeismicLineModel.id)
                .scalar_subquery()
                .label("shot_point_count"),
            )
            .where(SeismicLineModel.segy_file_id == file_id)
            .order_by(SeismicLineModel.id)
            .limit(1)
        ).first()

        if row is None:
            return None

        geom = to_shape(row[3])
        return {
            "type": "Feature",
            "geometry": geometry_to_geojson(geom),
            "properties": {
                "id": row[0],
                "line_id": row[1],
                "point_count": row[2],
                "trace_count": row[4],
                "shot_point_count": row[5],
                "start_coordinate": list(geom.coords[0]),
                "end_coordinate": list(geom.coords[-1]),
                "segy_file_id": file_id,
                "srid": 4326,
                "source": "postgis",
            },
        }

    def lines(self, file_id: int, line_id: int | None = None, bbox: str | None = None, offset: int = 0, limit: int = 1000) -> dict[str, Any]:
        from app.models import SeismicLineModel, SeismicShotPointModel, SeismicTraceModel

        query = select(
            SeismicLineModel.id,
            SeismicLineModel.line_id,
            SeismicLineModel.point_count,
            SeismicLineModel.geometry,
            select(func.count(SeismicTraceModel.id))
            .where(SeismicTraceModel.seismic_line_id == SeismicLineModel.id)
            .scalar_subquery()
            .label("trace_count"),
            select(func.count(SeismicShotPointModel.id))
            .where(SeismicShotPointModel.seismic_line_id == SeismicLineModel.id)
            .scalar_subquery()
            .label("shot_point_count"),
        ).where(SeismicLineModel.segy_file_id == file_id)
        if line_id is not None:
            query = query.where(SeismicLineModel.id == line_id)

        polygon = self._bbox_polygon(bbox)
        if polygon is not None:
            query = query.where(SeismicLineModel.geometry.intersects(polygon))

        rows = self.session.execute(
            query.order_by(SeismicLineModel.id).offset(offset).limit(limit)
        ).all()

        features: list[dict[str, Any]] = []
        for line_row_id, line_name, point_count, geom, trace_count, shot_point_count in rows:
            shape = to_shape(geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry_to_geojson(shape),
                    "properties": {
                        "id": line_row_id,
                        "line_id": line_name,
                        "point_count": point_count,
                        "trace_count": trace_count,
                        "shot_point_count": shot_point_count,
                        "start_coordinate": list(shape.coords[0]),
                        "end_coordinate": list(shape.coords[-1]),
                        "segy_file_id": file_id,
                        "srid": 4326,
                        "source": "postgis",
                    },
                }
            )

        return feature_collection(features)

    def shot_points(
        self,
        file_id: int,
        shot_point_number: int | None = None,
        bbox: str | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> dict[str, Any]:
        from app.models import SeismicShotPointModel

        query = select(SeismicShotPointModel.id, SeismicShotPointModel.geometry).where(SeismicShotPointModel.segy_file_id == file_id)
        if shot_point_number is not None:
            query = query.where(SeismicShotPointModel.shot_point_number == shot_point_number)

        polygon = self._bbox_polygon(bbox)
        if polygon is not None:
            query = query.where(SeismicShotPointModel.geometry.intersects(polygon))

        rows = self.session.execute(
            query.order_by(SeismicShotPointModel.id).offset(offset).limit(limit)
        ).all()

        features: list[dict[str, Any]] = []
        for shot_id, geom in rows:
            shape = to_shape(geom) if geom is not None else None
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry_to_geojson(shape),
                    "properties": {
                        "id": shot_id,
                        "segy_file_id": file_id,
                        "srid": 4326,
                        "source": "postgis",
                    },
                }
            )

        return feature_collection(features)

    def traces(
        self,
        file_id: int,
        line_id: int | None = None,
        bbox: str | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> dict[str, Any]:
        from app.models import SeismicTraceModel

        query = select(SeismicTraceModel.id, SeismicTraceModel.geometry).where(SeismicTraceModel.segy_file_id == file_id)
        if line_id is not None:
            query = query.where(SeismicTraceModel.seismic_line_id == line_id)

        polygon = self._bbox_polygon(bbox)
        if polygon is not None:
            query = query.where(SeismicTraceModel.geometry.intersects(polygon))

        rows = self.session.execute(
            query.order_by(SeismicTraceModel.id).offset(offset).limit(limit)
        ).all()

        features: list[dict[str, Any]] = []
        for trace_id, geom in rows:
            shape = to_shape(geom)
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry_to_geojson(shape),
                    "properties": {
                        "id": trace_id,
                        "segy_file_id": file_id,
                        "srid": 4326,
                        "source": "postgis",
                    },
                }
            )

        return feature_collection(features)

    def clip_lines_by_polygon(
        self,
        file_id: int,
        polygon_geojson: dict[str, Any],
        line_id: int | None = None,
    ) -> dict[str, Any]:
        import math
        from shapely.geometry import shape
        from shapely.ops import transform

        def lonlat_to_3857(x: float, y: float) -> tuple[float, float]:
            r_major = 6378137.0
            x_m = r_major * math.radians(x)
            lat = max(min(y, 89.5), -89.5)
            y_m = r_major * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
            return x_m, y_m

        def m3857_to_lonlat(x: float, y: float) -> tuple[float, float]:
            r_major = 6378137.0
            lon = math.degrees(x / r_major)
            lat = math.degrees(2.0 * math.atan(math.exp(y / r_major)) - math.pi / 2.0)
            return lon, lat

        poly_shape_4326 = shape(polygon_geojson)
        poly_shape_3857 = transform(lambda x, y, *a: lonlat_to_3857(x, y), poly_shape_4326)

        lines_collection = self.lines(file_id, line_id=line_id, limit=10000)

        out_features: list[dict[str, Any]] = []
        for feat in lines_collection.get("features", []):
            if not feat.get("geometry"):
                continue
            line_geom_4326 = shape(feat["geometry"])
            line_geom_3857 = transform(lambda x, y, *a: lonlat_to_3857(x, y), line_geom_4326)

            inside_3857 = line_geom_3857.intersection(poly_shape_3857)
            outside_3857 = line_geom_3857.difference(poly_shape_3857)

            if not inside_3857.is_empty:
                inside_4326 = transform(lambda x, y, *a: m3857_to_lonlat(x, y), inside_3857)
                out_features.append({
                    "type": "Feature",
                    "geometry": geometry_to_geojson(inside_4326),
                    "properties": {**feat["properties"], "is_inside": True},
                })

            if not outside_3857.is_empty:
                outside_4326 = transform(lambda x, y, *a: m3857_to_lonlat(x, y), outside_3857)
                out_features.append({
                    "type": "Feature",
                    "geometry": geometry_to_geojson(outside_4326),
                    "properties": {**feat["properties"], "is_inside": False},
                })

        return feature_collection(out_features)
