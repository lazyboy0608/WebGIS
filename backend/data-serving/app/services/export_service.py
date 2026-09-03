import csv
import io
import time
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

    def get_raw_file_download_url(self, segy_file_id: int) -> dict:
        """
        Generate presigned download URL for the raw SEG-Y file stored in MinIO.
        """
        segy_file = self.session.get(SegyFileModel, segy_file_id)
        if segy_file is None:
            raise ValueError(f"SEG-Y file with id={segy_file_id} not found")

        object_name = segy_file.file_path.replace("\\", "/").lstrip("/")

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
