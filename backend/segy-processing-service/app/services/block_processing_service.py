import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

import geopandas as gpd
from shapely import force_2d
from shapely.geometry import Polygon, MultiPolygon
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import processing_redis
from app.infrastructure.database.models import SeismicBlockModel
from app.infrastructure.storage.minio_file_storage import MinioFileStorage


class BlockProcessingService:
    def __init__(self, db: Session):
        self.db = db
        self.minio_storage = MinioFileStorage(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            bucket_name=settings.MINIO_BUCKET_BLOCKS_RAW,
        )

    def process_shapefile_zip(
        self,
        zip_bytes: bytes,
        filename: str,
        user_id: Optional[int] = None,
    ) -> List[SeismicBlockModel]:
        """
        1. Save raw zip file to MinIO (bucket: blocks-raw-inputs).
        2. Extract zip file content.
        3. Load shapefile with GeoPandas.
        4. Reproject/Force CRS to EPSG:4326 and run make_valid().
        5. Extract 'Block_id' attribute as block_code.
        6. Calculate area in km² and save records to seismic_blocks table in PostGIS.
        """
        # Step 1: Upload raw zip to MinIO
        minio_path = self.minio_storage.save(filename, zip_bytes)
        source_file_key = str(minio_path)

        imported_blocks: List[SeismicBlockModel] = []

        # Step 2: Extract zip to temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / filename
            zip_path.write_bytes(zip_bytes)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Find .shp file
            shp_files = list(Path(tmp_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("Không tìm thấy file .shp trong file zip đã tải lên.")

            shp_path = shp_files[0]

            # Step 3: Load with GeoPandas
            gdf = gpd.read_file(shp_path)
            if gdf.empty:
                raise ValueError("File Shapefile rỗng, không chứa đối tượng hình học nào.")

            # Step 4: CRS handling & Reproject to EPSG:4326
            if gdf.crs is not None:
                if gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
            else:
                # Force to EPSG:4326 if unassigned
                gdf = gdf.set_crs(epsg=4326, allow_override=True)

            # Fix invalid geometries
            gdf["geometry"] = gdf["geometry"].make_valid()

            # Calculate area in km² using Web Mercator EPSG:3857 (or metric projection)
            gdf_metric = gdf.to_crs(epsg=3857)

            # Detect Block Code field (prioritize 'Block_id', then case-insensitive match)
            block_code_col = None
            candidate_cols = ["Block_id", "block_id", "BLOCK_ID", "block_code", "Mã lô", "MA_LO", "Block", "BLOCK"]
            for col in gdf.columns:
                if col in candidate_cols or col.lower() == "block_id":
                    block_code_col = col
                    break

            # Fallback if no matching column found
            if not block_code_col:
                for col in gdf.columns:
                    if "block" in col.lower() or "lô" in col.lower():
                        block_code_col = col
                        break

            # Detect Operator field
            operator_col = None
            operator_candidates = ["operator", "Operator", "OPERATOR", "nha_dieu_hanh", "nha_thau", "Nha_thau", "NHA_THAU", "nhathau", "contractor", "Contractor", "company", "Company"]
            for col in gdf.columns:
                if col in operator_candidates or "operator" in col.lower() or "thau" in col.lower():
                    operator_col = col
                    break

            # Detect Basin field
            basin_col = None
            basin_candidates = ["Basin_Name", "basin_name", "BASIN_NAME", "Basin", "basin", "BASIN", "Be_tram_tich", "BE_TRAM_TICH", "be_tram_tich"]
            for col in gdf.columns:
                if col in basin_candidates or "basin" in col.lower() or "tram_tich" in col.lower():
                    basin_col = col
                    break

            # Explode MultiPolygons if necessary
            gdf = gdf.explode(index_parts=False).reset_index(drop=True)
            gdf_metric = gdf_metric.explode(index_parts=False).reset_index(drop=True)

            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue

                # Ensure 2D geometry (strip Z dimension if present in 3D Shapefiles/GeoJSON)
                geom = force_2d(geom)

                if not isinstance(geom, (Polygon, MultiPolygon)):
                    continue

                # Extract block_code
                if block_code_col and block_code_col in row and row[block_code_col] is not None:
                    code_val = str(row[block_code_col]).strip()
                else:
                    code_val = f"Block_{idx + 1}"

                # Extract operator
                op_val = None
                if operator_col and operator_col in row and row[operator_col] is not None:
                    op_val = str(row[operator_col]).strip()

                # Extract basin_name
                basin_val = None
                if basin_col and basin_col in row and row[basin_col] is not None:
                    basin_val = str(row[basin_col]).strip()

                # Calculate area in km2
                metric_geom = gdf_metric.iloc[idx].geometry
                area_km2 = round(metric_geom.area / 1_000_000.0, 4) if metric_geom else 0.0

                wkt_str = geom.wkt

                block_model = SeismicBlockModel(
                    user_id=user_id,
                    block_code=code_val,
                    operator=op_val,
                    basin_name=basin_val,
                    area_km2=area_km2,
                    status="active",
                    source_file=source_file_key,
                    geometry=func.ST_Force2D(func.ST_Multi(func.ST_GeomFromText(wkt_str, 4326))) if isinstance(geom, MultiPolygon) else func.ST_Force2D(func.ST_GeomFromText(wkt_str, 4326)),
                )
                self.db.add(block_model)
                imported_blocks.append(block_model)

            self.db.commit()
            processing_redis.invalidate_data_cache_pattern("blocks:*")
            for b in imported_blocks:
                self.db.refresh(b)

        return imported_blocks
