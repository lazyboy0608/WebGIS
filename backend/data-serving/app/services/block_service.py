import json
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import SeismicBlockModel


class BlockService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_blocks(self, status_filter: Optional[str] = "active") -> List[SeismicBlockModel]:
        query = self.session.query(SeismicBlockModel)
        if status_filter:
            query = query.filter(SeismicBlockModel.status == status_filter)
        return query.order_by(SeismicBlockModel.id.desc()).all()

    def get_block_by_id(self, block_id: int) -> Optional[SeismicBlockModel]:
        return self.session.query(SeismicBlockModel).filter(SeismicBlockModel.id == block_id).first()

    def get_blocks_geojson(self, status_filter: Optional[str] = "active") -> Dict[str, Any]:
        query_str = """
            SELECT 
                id, 
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
        """
        params = {}
        if status_filter:
            query_str += " WHERE status = :status_filter"
            params["status_filter"] = status_filter

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

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def split_block(
        self,
        block_id: int,
        split_line_wkt: str,
        new_block_codes: Optional[List[str]] = None,
    ) -> List[SeismicBlockModel]:
        """
        Split a seismic block polygon into multiple sub-polygons using PostGIS ST_Split.
        """
        parent_block = self.get_block_by_id(block_id)
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

        child_blocks: List[SeismicBlockModel] = []
        for idx, row in enumerate(res):
            geom_wkt = row.geom_wkt
            calculated_area = round(float(row.area_km2), 4) if row.area_km2 else 0.0

            if new_block_codes and idx < len(new_block_codes) and new_block_codes[idx].strip():
                code = new_block_codes[idx].strip()
            else:
                code = f"{parent_block.block_code}_{chr(65 + idx)}"

            insert_sql = text("""
                INSERT INTO seismic_blocks (block_code, operator, basin_name, area_km2, status, parent_id, source_file, geometry)
                VALUES (:code, :operator, :basin_name, :area, 'active', :parent_id, :source_file, ST_Force2D(ST_GeomFromText(:wkt, 4326)))
                RETURNING id;
            """)
            
            inserted_id = self.session.execute(insert_sql, {
                "code": code,
                "operator": parent_block.operator,
                "basin_name": parent_block.basin_name,
                "area": calculated_area,
                "parent_id": parent_block.id,
                "source_file": parent_block.source_file,
                "wkt": geom_wkt,
            }).scalar_one()

            child_model = self.get_block_by_id(inserted_id)
            if child_model:
                child_blocks.append(child_model)

        self.session.commit()
        return child_blocks

    def undo_split(self, parent_block_id: int) -> tuple:
        """
        Hoàn tác thao tác tách lô (Command Pattern undo):
        1. Xóa tất cả các lô con (parent_id = parent_block_id).
        2. Khôi phục lô cha về status = 'active'.
        Toàn bộ thực hiện trong 1 transaction nguyên tử.

        Returns:
            (parent_block, deleted_child_ids)
        """
        parent_block = self.get_block_by_id(parent_block_id)
        if not parent_block:
            raise ValueError(f"Không tìm thấy Lô địa chấn với id={parent_block_id}")

        if parent_block.status != "split":
            raise ValueError(
                f"Lô địa chấn id={parent_block_id} không ở trạng thái 'split' "
                f"(trạng thái hiện tại: '{parent_block.status}'). Không thể hoàn tác."
            )

        # Lấy danh sách ID các lô con trước khi xóa
        children = (
            self.session.query(SeismicBlockModel)
            .filter(SeismicBlockModel.parent_id == parent_block_id)
            .all()
        )
        deleted_child_ids = [c.id for c in children]

        if not deleted_child_ids:
            # Không có lô con — vẫn phục hồi lô cha cho nhất quán
            pass
        else:
            # Xóa toàn bộ lô con trong 1 câu lệnh
            delete_sql = text(
                "DELETE FROM seismic_blocks WHERE parent_id = :parent_id"
            )
            self.session.execute(delete_sql, {"parent_id": parent_block_id})

        # Phục hồi lô cha
        parent_block.status = "active"
        self.session.add(parent_block)
        self.session.commit()
        self.session.refresh(parent_block)

        return parent_block, deleted_child_ids

