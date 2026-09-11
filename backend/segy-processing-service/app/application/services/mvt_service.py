from typing import Sequence
from sqlalchemy import text
from sqlalchemy.orm import Session


class MVTService:
    """Service to generate Mapbox Vector Tiles (MVT) directly from PostGIS."""

    def __init__(self, session: Session):
        self.session = session

    def generate_tile(
        self,
        z: int,
        x: int,
        y: int,
        file_ids: Sequence[int] | None = None,
        file_id: int | None = None,
        layers: Sequence[str] | None = None,
    ) -> bytes:
        target_layers = list(layers) if layers else ["lines", "shot_points", "traces"]
        active_file_ids = list(file_ids) if file_ids else ([file_id] if file_id is not None else None)

        # ── 3-Level of Detail (LOD) based on Zoom level z ─────────────
        # LOD 1 (z < 10):  Overview  → Only 'lines'
        # LOD 2 (10<=z<14): Regional → 'lines' + 'shot_points'
        # LOD 3 (z >= 14):  Detailed → 'lines' + 'shot_points' + 'traces'
        lod_layers: list[str] = []
        if "lines" in target_layers:
            lod_layers.append("lines")
        if "shot_points" in target_layers and z >= 10:
            lod_layers.append("shot_points")
        if "traces" in target_layers and z >= 14:
            lod_layers.append("traces")

        file_filter = ""
        params: dict[str, object] = {"z": z, "x": x, "y": y}
        if active_file_ids:
            file_filter = "AND segy_file_id = ANY(:file_ids)"
            params["file_ids"] = list(active_file_ids)

        mvt_parts: list[bytes] = []

        if "lines" in lod_layers:
            sql_lines = f"""
            WITH tile_env AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS bbox
            ),
            mvtgeom AS (
                SELECT
                    l.id,
                    l.segy_file_id,
                    l.line_id,
                    ST_AsMVTGeom(
                        ST_Transform(l.geometry, 3857),
                        t.bbox,
                        4096,
                        256,
                        true
                    ) AS geom
                FROM seismic_lines l, tile_env t
                WHERE l.geometry IS NOT NULL
                  AND ST_XMin(l.geometry) >= -180 AND ST_XMax(l.geometry) <= 180
                  AND ST_YMin(l.geometry) >= -90 AND ST_YMax(l.geometry) <= 90
                  AND ST_Transform(l.geometry, 3857) && t.bbox
                {file_filter}
            )
            SELECT ST_AsMVT(mvtgeom, 'lines', 4096, 'geom') FROM mvtgeom;
            """
            try:
                res = self.session.execute(text(sql_lines), params).scalar()
                if res and isinstance(res, bytes):
                    mvt_parts.append(res)
            except Exception:
                pass

        if "shot_points" in lod_layers:
            sql_sp = f"""
            WITH tile_env AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS bbox
            ),
            mvtgeom AS (
                SELECT
                    sp.id,
                    sp.segy_file_id,
                    sp.shot_point_number,
                    ST_AsMVTGeom(
                        ST_Transform(sp.geometry, 3857),
                        t.bbox,
                        4096,
                        256,
                        true
                    ) AS geom
                FROM seismic_shot_points sp, tile_env t
                WHERE sp.geometry IS NOT NULL
                  AND ST_XMin(sp.geometry) >= -180 AND ST_XMax(sp.geometry) <= 180
                  AND ST_YMin(sp.geometry) >= -90 AND ST_YMax(sp.geometry) <= 90
                  AND ST_Transform(sp.geometry, 3857) && t.bbox
                {file_filter}
            )
            SELECT ST_AsMVT(mvtgeom, 'shot_points', 4096, 'geom') FROM mvtgeom;
            """
            try:
                res = self.session.execute(text(sql_sp), params).scalar()
                if res and isinstance(res, bytes):
                    mvt_parts.append(res)
            except Exception:
                pass

        if "traces" in lod_layers:
            sql_traces = f"""
            WITH tile_env AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS bbox
            ),
            mvtgeom AS (
                SELECT
                    tr.id,
                    tr.segy_file_id,
                    tr.trace_index,
                    ST_AsMVTGeom(
                        ST_Transform(tr.geometry, 3857),
                        t.bbox,
                        4096,
                        256,
                        true
                    ) AS geom
                FROM seismic_traces tr, tile_env t
                WHERE tr.geometry IS NOT NULL
                  AND ST_XMin(tr.geometry) >= -180 AND ST_XMax(tr.geometry) <= 180
                  AND ST_YMin(tr.geometry) >= -90 AND ST_YMax(tr.geometry) <= 90
                  AND ST_Transform(tr.geometry, 3857) && t.bbox
                {file_filter}
            )
            SELECT ST_AsMVT(mvtgeom, 'traces', 4096, 'geom') FROM mvtgeom;
            """
            try:
                res = self.session.execute(text(sql_traces), params).scalar()
                if res and isinstance(res, bytes):
                    mvt_parts.append(res)
            except Exception:
                pass

        return b"".join(mvt_parts)
