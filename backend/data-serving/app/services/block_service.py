import io
import json
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import SeismicBlockModel
from app.core.redis_client import redis_cache

logger = logging.getLogger("webgis.block")


class BlockService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_blocks(
        self,
        status_filter: Optional[str] = "active",
        user_id: Optional[int] = None,
    ) -> List[SeismicBlockModel]:
        query = self.session.query(SeismicBlockModel)
        if status_filter:
            query = query.filter(SeismicBlockModel.status == status_filter)
        if user_id is not None:
            query = query.filter(SeismicBlockModel.user_id == user_id)
        else:
            query = query.filter(SeismicBlockModel.user_id.is_(None))
        return query.order_by(SeismicBlockModel.id.desc()).all()

    def get_block_by_id(
        self,
        block_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[SeismicBlockModel]:
        query = self.session.query(SeismicBlockModel).filter(SeismicBlockModel.id == block_id)
        if user_id is not None:
            query = query.filter((SeismicBlockModel.user_id == user_id) | (SeismicBlockModel.user_id.is_(None)))
        return query.first()

    def get_blocks_geojson(
        self,
        status_filter: Optional[str] = "active",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        cache_key = f"blocks:geojson:{user_id or 'anon'}:{status_filter or 'all'}"
        cached_geojson = redis_cache.get_json(cache_key)
        if cached_geojson is not None:
            logger.info(f"[REDIS CACHE HIT] {cache_key}")
            return cached_geojson

        logger.info(f"[REDIS CACHE MISS] {cache_key} -> Querying PostGIS...")

        query_str = """
            SELECT 
                id, 
                user_id,
                block_code, 
                operator, 
                basin_name, 
                area_km2, 
                status, 
                parent_id, 
                source_file,
                created_at,
                updated_at,
                ST_AsGeoJSON(geometry) as geojson
            FROM seismic_blocks
            WHERE 1=1
        """
        params: dict[str, Any] = {}
        if status_filter:
            query_str += " AND status = :status_filter"
            params["status_filter"] = status_filter
        if user_id is not None:
            query_str += " AND user_id = :user_id"
            params["user_id"] = user_id
        else:
            query_str += " AND user_id IS NULL"

        query_str += " ORDER BY id DESC;"

        rows = self.session.execute(text(query_str), params).fetchall()

        features = []
        for r in rows:
            geom_dict = json.loads(r.geojson) if r.geojson else None
            if not geom_dict:
                continue

            feature = {
                "type": "Feature",
                "geometry": geom_dict,
                "properties": {
                    "id": r.id,
                    "user_id": r.user_id,
                    "block_code": r.block_code,
                    "operator": r.operator,
                    "basin_name": r.basin_name,
                    "area_km2": r.area_km2,
                    "status": r.status,
                    "parent_id": r.parent_id,
                    "source_file": r.source_file,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                },
            }
            features.append(feature)

        payload = {
            "type": "FeatureCollection",
            "features": features,
        }
        redis_cache.set_json(cache_key, payload)
        return payload

    def split_block(
        self,
        block_id: int,
        split_line_wkt: str,
        new_block_codes: Optional[List[str]] = None,
        user_id: Optional[int] = None,
    ) -> List[SeismicBlockModel]:
        """
        Split a seismic block polygon into multiple sub-polygons using PostGIS ST_Split.
        """
        parent_block = self.get_block_by_id(block_id, user_id=user_id)
        if not parent_block:
            raise ValueError(f"Không tìm thấy Lô địa chấn với id={block_id}")

        if parent_block.status != "active":
            raise ValueError(f"Lô địa chấn id={block_id} không ở trạng thái 'active' (trạng thái hiện tại: {parent_block.status})")

        # Execute PostGIS ST_Split
        split_sql = text("""
            SELECT 
                ST_AsText((ST_Dump(ST_Split(b.geometry, ST_GeomFromText(:wkt, 4326)))).geom) as geom_wkt,
                ST_Area(ST_Transform((ST_Dump(ST_Split(b.geometry, ST_GeomFromText(:wkt, 4326)))).geom, 3857)) / 1000000.0 as area_km2
            FROM seismic_blocks b
            WHERE b.id = :block_id;
        """)

        res = self.session.execute(split_sql, {"wkt": split_line_wkt, "block_id": block_id}).fetchall()

        if not res or len(res) < 2:
            raise ValueError("Đường cắt không chia đứt Lô thành các phần riêng biệt. Vui lòng vẽ đường cắt đâm xuyên qua toàn bộ ranh giới Lô.")

        # Update parent status to 'split'
        parent_block.status = "split"
        self.session.add(parent_block)

        effective_user_id = parent_block.user_id if parent_block.user_id is not None else user_id

        child_blocks: List[SeismicBlockModel] = []
        for idx, row in enumerate(res):
            geom_wkt = row.geom_wkt
            calculated_area = round(float(row.area_km2), 4) if row.area_km2 else 0.0

            if new_block_codes and idx < len(new_block_codes) and new_block_codes[idx].strip():
                code = new_block_codes[idx].strip()
            else:
                code = f"{parent_block.block_code}_{chr(65 + idx)}"

            insert_sql = text("""
                INSERT INTO seismic_blocks (user_id, block_code, operator, basin_name, area_km2, status, parent_id, source_file, geometry)
                VALUES (:user_id, :code, :operator, :basin_name, :area, 'active', :parent_id, :source_file, ST_Force2D(ST_GeomFromText(:wkt, 4326)))
                RETURNING id;
            """)
            
            inserted_id = self.session.execute(insert_sql, {
                "user_id": effective_user_id,
                "code": code,
                "operator": parent_block.operator,
                "basin_name": parent_block.basin_name,
                "area": calculated_area,
                "parent_id": parent_block.id,
                "source_file": parent_block.source_file,
                "wkt": geom_wkt,
            }).scalar_one()

            child_model = self.get_block_by_id(inserted_id, user_id=effective_user_id)
            if child_model:
                child_blocks.append(child_model)

        self.session.commit()
        redis_cache.delete_pattern("blocks:*")
        return child_blocks

    def undo_split(
        self,
        parent_block_id: int,
        user_id: Optional[int] = None,
    ) -> tuple:
        """
        Hoàn tác thao tác tách lô (Command Pattern undo):
        1. Xóa tất cả các lô con (parent_id = parent_block_id).
        2. Khôi phục lô cha về status = 'active'.
        Toàn bộ thực hiện trong 1 transaction nguyên tử.

        Returns:
            (parent_block, deleted_child_ids)
        """
        parent_block = self.get_block_by_id(parent_block_id, user_id=user_id)
        if not parent_block:
            raise ValueError(f"Không tìm thấy Lô địa chấn với id={parent_block_id}")

        if parent_block.status != "split":
            raise ValueError(
                f"Lô địa chấn id={parent_block_id} không ở trạng thái 'split' "
                f"(trạng thái hiện tại: '{parent_block.status}'). Không thể hoàn tác."
            )

        # Lấy danh sách ID các lô con trước khi xóa
        child_query = self.session.query(SeismicBlockModel).filter(SeismicBlockModel.parent_id == parent_block_id)
        if user_id is not None:
            child_query = child_query.filter((SeismicBlockModel.user_id == user_id) | (SeismicBlockModel.user_id.is_(None)))
        children = child_query.all()
        deleted_child_ids = [c.id for c in children]

        if not deleted_child_ids:
            pass
        else:
            delete_sql = text(
                "DELETE FROM seismic_blocks WHERE parent_id = :parent_id"
            )
            self.session.execute(delete_sql, {"parent_id": parent_block_id})

        # Phục hồi lô cha
        parent_block.status = "active"
        self.session.add(parent_block)
        self.session.commit()
        redis_cache.delete_pattern("blocks:*")
        self.session.refresh(parent_block)

        return parent_block, deleted_child_ids

    def export_block_excel(
        self,
        block_id: int,
        user_id: Optional[int] = None,
    ) -> tuple[bytes, str]:
        """
        Trích xuất tất cả các điểm đỉnh ranh giới Lô địa chấn (Block) qua PostGIS ST_DumpPoints
        và đóng gói thành file Excel (.xlsx) với các cột [X, Y, Block, Basin].
        """
        parent_block = self.get_block_by_id(block_id, user_id=user_id)
        if not parent_block:
            raise ValueError(f"Không tìm thấy Lô địa chấn với id={block_id}")

        dump_sql = text("""
            SELECT 
                ST_X((dp).geom) AS x,
                ST_Y((dp).geom) AS y,
                b.block_code AS block,
                b.basin_name AS basin
            FROM seismic_blocks b,
                 LATERAL ST_DumpPoints(b.geometry) AS dp
            WHERE b.id = :block_id
            ORDER BY (dp).path;
        """)

        rows = self.session.execute(dump_sql, {"block_id": block_id}).fetchall()
        if not rows:
            raise ValueError(f"Lô địa chấn id={block_id} không có dữ liệu tọa độ không gian.")

        rows_data = []
        for r in rows:
            rows_data.append({
                "X": float(r.x) if r.x is not None else None,
                "Y": float(r.y) if r.y is not None else None,
                "Block": r.block or parent_block.block_code,
                "Basin": r.basin or parent_block.basin_name or "",
            })

        df = pd.DataFrame(rows_data, columns=["X", "Y", "Block", "Basin"])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Blk")
        output.seek(0)

        clean_code = (parent_block.block_code or f"Block_{block_id}").replace("/", "-").replace("&", "_")
        filename = f"Block_{clean_code}_Coordinates.xlsx"
        return output.getvalue(), filename

    def delete_all_blocks(self, user_id: Optional[int] = None) -> int:
        """Xóa tất cả các Lô địa chấn thuộc quyền sở hữu của user."""
        query = self.session.query(SeismicBlockModel)
        if user_id is not None:
            query = query.filter(SeismicBlockModel.user_id == user_id)
        else:
            query = query.filter(SeismicBlockModel.user_id.is_(None))
        count = query.delete(synchronize_session=False)
        self.session.commit()
        redis_cache.delete_pattern("blocks:*")
        return count

    def delete_blocks_by_source_file(
        self,
        source_file: str,
        user_id: Optional[int] = None,
    ) -> int:
        """Xóa tất cả các Lô địa chấn thuộc một file nguồn cụ thể của user."""
        filename_only = source_file.split("/")[-1].split("\\")[-1]
        query = self.session.query(SeismicBlockModel).filter(
            (SeismicBlockModel.source_file == source_file) |
            (SeismicBlockModel.source_file.like(f"%/{filename_only}")) |
            (SeismicBlockModel.source_file.like(f"%\\{filename_only}")) |
            (SeismicBlockModel.source_file == filename_only)
        )
        if user_id is not None:
            query = query.filter(SeismicBlockModel.user_id == user_id)
        else:
            query = query.filter(SeismicBlockModel.user_id.is_(None))

        count = query.delete(synchronize_session=False)
        self.session.commit()
        redis_cache.delete_pattern("blocks:*")
        return count



