import csv
import io
import os
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from shapely import from_wkb


from app.config import settings
from app.infrastructure.storage.minio_client import MinioClientManager, minio_manager
from app.models import SegyFileModel, SeismicShotPointModel, SeismicTraceModel


class ExportService:
    """Service to export processed seismic data and store artifacts in MinIO."""

    def __init__(
        self,
        session: Session,
        storage_manager: MinioClientManager | None = None,
    ) -> None:
        self.session = session
        self.storage = storage_manager or minio_manager

    def export_traces_csv(self, segy_file_id: int) -> dict:
        """
        Export traces coordinates for a SEG-Y file to CSV, upload to MinIO,
        and return the presigned download URL.

        CSV columns: Trace, SP, Lon, Lat  (1 SEG-Y file = 1 CSV file)
        """
        segy_file = self.session.get(SegyFileModel, segy_file_id)
        if segy_file is None:
            raise ValueError(f"SEG-Y file with id={segy_file_id} not found")

        stmt = (
            select(
                SeismicTraceModel.trace_index,
                SeismicShotPointModel.shot_point_number,
                SeismicTraceModel.geometry,
            )
            .outerjoin(
                SeismicShotPointModel,
                SeismicTraceModel.shot_point_id == SeismicShotPointModel.id,
            )
            .where(SeismicTraceModel.segy_file_id == segy_file_id)
            .order_by(SeismicTraceModel.trace_index)
        )

        rows = self.session.execute(stmt).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Trace", "SP", "Lon", "Lat"])

        for row in rows:
            trace_idx, sp_num, geom = row
            lon, lat = "", ""
            if geom is not None:
                shape = from_wkb(bytes(geom.data))
                lon, lat = shape.x, shape.y
            writer.writerow(
                [trace_idx, sp_num if sp_num is not None else "", lon, lat]
            )

        csv_bytes = output.getvalue().encode("utf-8")
        timestamp = int(time.time())
        clean_base = segy_file.filename.rsplit(".", 1)[0]
        object_name = f"exports/{segy_file_id}/{clean_base}_traces_{timestamp}.csv"
        export_filename = f"{clean_base}_traces_{timestamp}.csv"

        # Upload to MinIO processed bucket
        self.storage.upload_bytes(
            bucket_name=settings.minio_bucket_processed,
            object_name=object_name,
            data=csv_bytes,
            content_type="text/csv",
        )

        download_url = self.storage.get_presigned_download_url(
            bucket_name=settings.minio_bucket_processed,
            object_name=object_name,
            filename=export_filename,
        )

        return {
            "segy_file_id": segy_file_id,
            "filename": export_filename,
            "object_name": object_name,
            "bucket": settings.minio_bucket_processed,
            "size_bytes": len(csv_bytes),
            "record_count": len(rows),
            "download_url": download_url,
        }

    def export_batch_csv(self, segy_file_ids: list[int]) -> list[dict]:
        """
        Export traces for each SEG-Y file in the list as a separate CSV.
        Returns a list of export results — 1 SEG-Y file = 1 CSV file.
        """
        results = []
        for file_id in segy_file_ids:
            result = self.export_traces_csv(file_id)
            results.append(result)
        return results

    def _resolve_raw_segy_path(self, segy_file: SegyFileModel) -> tuple[str, bool]:
        """
        Resolve raw SEG-Y file path for reading.
        Returns (resolved_file_path, is_temp_file).
        """
        import os
        import tempfile
        from pathlib import Path

        raw_path_str = segy_file.file_path
        path_obj = Path(raw_path_str)

        # 1. Direct path check
        if path_obj.exists() and path_obj.is_file():
            return str(path_obj.resolve()), False

        # 2. Check relative to workspace root
        workspace_root = Path(__file__).resolve().parents[3]  # d:\WebGIS
        clean_filename = Path(segy_file.filename).name

        candidates = [
            workspace_root / raw_path_str.lstrip("/\\"),
            workspace_root / "backend" / "segy-processing-service" / raw_path_str.lstrip("/\\"),
            workspace_root / "backend" / "segy-processing-service" / "storage" / "segy" / clean_filename,
            workspace_root / "backend" / "segy-processing-service" / "storage" / clean_filename,
            workspace_root / "backend" / "segy-processing-service" / "data" / clean_filename,
            workspace_root / "storage" / "segy" / clean_filename,
            workspace_root / "storage" / clean_filename,
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate.resolve()), False

        # 3. Download from MinIO
        raw_object_name = raw_path_str.replace("\\", "/").lstrip("/")
        object_candidates = []
        if raw_object_name.startswith("uploads/"):
            object_candidates.append(raw_object_name)
        else:
            object_candidates.append(f"uploads/{raw_object_name}")
            object_candidates.append(raw_object_name)
            object_candidates.append(f"uploads/{clean_filename}")
            object_candidates.append(clean_filename)

        temp_raw_fd, temp_raw_path = tempfile.mkstemp(suffix=".sgy")
        os.close(temp_raw_fd)

        for obj_name in object_candidates:
            try:
                self.storage.client.fget_object(
                    settings.minio_bucket_raw,
                    obj_name,
                    temp_raw_path,
                )
                return temp_raw_path, True
            except Exception:
                continue

        if os.path.exists(temp_raw_path):
            os.remove(temp_raw_path)

        raise ValueError(
            f"Raw SEG-Y file for id={segy_file.id} ({segy_file.filename}) not found on local disk at '{segy_file.file_path}' or in MinIO bucket '{settings.minio_bucket_raw}'."
        )

    def get_raw_file_download_url(self, segy_file_id: int) -> dict:
        """
        Generate presigned download URL for the raw SEG-Y file stored in MinIO.
        """
        segy_file = self.session.get(SegyFileModel, segy_file_id)
        if segy_file is None:
            raise ValueError(f"SEG-Y file with id={segy_file_id} not found")

        resolved_path, is_temp = self._resolve_raw_segy_path(segy_file)
        object_name = segy_file.file_path.replace("\\", "/").lstrip("/")
        if not object_name:
            clean_name = Path(segy_file.filename).name
            object_name = f"uploads/{clean_name}"

        # Ensure object is present in MinIO raw bucket for download
        try:
            self.storage.client.stat_object(settings.minio_bucket_raw, object_name)
        except Exception:
            try:
                self.storage.ensure_bucket(settings.minio_bucket_raw)
                self.storage.client.fput_object(
                    settings.minio_bucket_raw,
                    object_name,
                    resolved_path,
                )
            except Exception:
                pass

        if is_temp and os.path.exists(resolved_path):
            try:
                os.remove(resolved_path)
            except Exception:
                pass

        download_url = self.storage.get_presigned_download_url(
            bucket_name=settings.minio_bucket_raw,
            object_name=object_name,
            filename=segy_file.filename,
        )


        return {
            "segy_file_id": segy_file_id,
            "filename": segy_file.filename,
            "object_name": object_name,
            "bucket": settings.minio_bucket_raw,
            "download_url": download_url,
        }

    def export_polygon_segy(
        self,
        polygon_ring: list[list[float]],
        polygon_name: str = "spatial_filter",
        file_ids: list[int] | None = None,
    ) -> list[dict]:
        """
        Export line segments inside a polygon filter to individual SEG-Y (.sgy) files.
        One SEG-Y file is generated and returned per clipped seismic line.

        Coordinate headers (SRCX/SRCY, GroupX/GroupY, CDP-X/CDP-Y) are
        written in EPSG:4326 (geographic degrees) using the coordinates already
        stored in PostGIS (srid=4326), so the exported files are easy to
        inspect in viewers like SeiSee.  Coordinates are stored as integer
        milliarcseconds (SourceGroupScalar / ElevationScalar = -1000).
        """
        import os
        import re
        import tempfile
        import segyio
        from shapely import from_wkb
        from shapely.geometry import Polygon
        from app.models import SeismicLineModel

        if not polygon_ring or len(polygon_ring) < 3:
            raise ValueError("polygon_ring must contain at least 3 coordinates")

        # Ensure ring is closed
        ring_coords = list(polygon_ring)
        if ring_coords[0] != ring_coords[-1]:
            ring_coords.append(ring_coords[0])

        poly_shape = Polygon(ring_coords)

        # Query seismic lines
        line_stmt = select(SeismicLineModel).order_by(SeismicLineModel.id)
        if file_ids is not None and len(file_ids) > 0:
            line_stmt = line_stmt.where(SeismicLineModel.segy_file_id.in_(file_ids))

        lines = self.session.execute(line_stmt).scalars().all()

        results = []
        clean_poly_name = re.sub(r"[^\w\-]", "_", polygon_name) or "polygon"
        timestamp = int(time.time())

        # Cache downloaded/resolved raw SEG-Y files per segy_file_id
        downloaded_raw_files: dict[int, tuple[str, bool]] = {}

        try:
            for line in lines:
                segy_file = self.session.get(SegyFileModel, line.segy_file_id)
                if segy_file is None:
                    continue

                # Query traces for this line, collecting geometry (already EPSG:4326 in PostGIS)
                trace_stmt = (
                    select(SeismicTraceModel.trace_index, SeismicTraceModel.geometry)
                    .where(SeismicTraceModel.seismic_line_id == line.id)
                    .order_by(SeismicTraceModel.trace_index)
                )
                traces = self.session.execute(trace_stmt).all()

                # Determine which traces fall inside the polygon, and record their lon/lat
                # from PostGIS (already in EPSG:4326 — no reprojection needed).
                inside_indices: list[int] = []
                # trace_index → (lon, lat) in EPSG:4326
                trace_lonlat: dict[int, tuple[float, float]] = {}

                for trace_idx, geom in traces:
                    if geom is not None:
                        pt_shape = from_wkb(bytes(geom.data))
                        if poly_shape.intersects(pt_shape) or poly_shape.contains(pt_shape):
                            inside_indices.append(trace_idx)
                            # pt_shape.x = longitude, pt_shape.y = latitude (EPSG:4326)
                            trace_lonlat[trace_idx] = (pt_shape.x, pt_shape.y)

                if not inside_indices:
                    continue

                # Ensure raw file path is resolved
                if line.segy_file_id not in downloaded_raw_files:
                    downloaded_raw_files[line.segy_file_id] = self._resolve_raw_segy_path(segy_file)

                temp_raw_path, _ = downloaded_raw_files[line.segy_file_id]

                # Create clipped SEG-Y file
                temp_dst_fd, temp_dst_path = tempfile.mkstemp(suffix=".sgy")
                os.close(temp_dst_fd)

                try:
                    with segyio.open(temp_raw_path, "r", ignore_geometry=True) as src:
                        spec = segyio.spec()
                        spec.sorting = getattr(src, "sorting", 1)
                        spec.format = src.format
                        spec.samples = src.samples
                        spec.tracecount = len(inside_indices)

                        with segyio.create(temp_dst_path, spec) as dst:
                            dst.text[0] = src.text[0]
                            for k, v in src.bin.items():
                                try:
                                    dst.bin[k] = v
                                except Exception:
                                    pass
                            dst.bin[segyio.BinField.Traces] = len(inside_indices)

                            for new_idx, orig_idx in enumerate(inside_indices):
                                # Copy all original headers and trace data
                                dst.header[new_idx] = src.header[orig_idx]
                                dst.header[new_idx][segyio.TraceField.TRACE_SEQUENCE_LINE] = new_idx + 1
                                dst.header[new_idx][segyio.TraceField.TRACE_SEQUENCE_FILE] = new_idx + 1
                                dst.trace[new_idx] = src.trace[orig_idx]

                                # --- Overwrite coordinate headers with EPSG:4326 values ---
                                # Use coordinates from PostGIS (already geographic, no reprojection needed).
                                # Store as integer milliarcseconds: scalar = -1000 → divide by 1000 to get degrees.
                                if orig_idx in trace_lonlat:
                                    lon, lat = trace_lonlat[orig_idx]
                                    lon_ms = int(round(lon * 1000))  # milliarcseconds
                                    lat_ms = int(round(lat * 1000))

                                    dst.header[new_idx].update({
                                        # Byte 71-72: coordinate scalar (SourceGroupScalar)
                                        segyio.TraceField.SourceGroupScalar: -1000,
                                        # Byte 69-70: elevation scalar (keep consistent)
                                        segyio.TraceField.ElevationScalar: -1000,
                                        # SRCX / SRCY (bytes 73-76 / 77-80)
                                        segyio.TraceField.SourceX: lon_ms,
                                        segyio.TraceField.SourceY: lat_ms,
                                        # GroupX / GroupY (bytes 81-84 / 85-88)
                                        segyio.TraceField.GroupX: lon_ms,
                                        segyio.TraceField.GroupY: lat_ms,
                                        # CDP-X / CDP-Y (bytes 181-184 / 185-188)
                                        segyio.TraceField.CDP_X: lon_ms,
                                        segyio.TraceField.CDP_Y: lat_ms,
                                    })

                    with open(temp_dst_path, "rb") as f:
                        sgy_bytes = f.read()

                    clean_line_id = re.sub(r"[^\w\-]", "_", line.line_id) or f"line_{line.id}"
                    export_filename = f"{clean_line_id}_{clean_poly_name}_{timestamp}.sgy"
                    object_name = f"exports/{line.segy_file_id}/{export_filename}"

                    self.storage.upload_bytes(
                        bucket_name=settings.minio_bucket_processed,
                        object_name=object_name,
                        data=sgy_bytes,
                        content_type="application/octet-stream",
                    )

                    download_url = self.storage.get_presigned_download_url(
                        bucket_name=settings.minio_bucket_processed,
                        object_name=object_name,
                        filename=export_filename,
                    )

                    results.append(
                        {
                            "segy_file_id": line.segy_file_id,
                            "line_id": line.line_id,
                            "filename": export_filename,
                            "object_name": object_name,
                            "bucket": settings.minio_bucket_processed,
                            "size_bytes": len(sgy_bytes),
                            "trace_count": len(inside_indices),
                            "download_url": download_url,
                        }
                    )
                finally:
                    if os.path.exists(temp_dst_path):
                        os.remove(temp_dst_path)

        finally:
            for raw_path, is_temp in downloaded_raw_files.values():
                if is_temp and os.path.exists(raw_path):
                    try:
                        os.remove(raw_path)
                    except Exception:
                        pass

        return results
