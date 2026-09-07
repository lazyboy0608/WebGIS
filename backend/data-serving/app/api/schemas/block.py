from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class BlockResponse(BaseModel):
    id: int
    block_code: str
    operator: Optional[str] = None
    basin_name: Optional[str] = None
    area_km2: Optional[float] = None
    status: str
    parent_id: Optional[int] = None
    source_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlockGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class BlockGeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[BlockGeoJSONFeature]


class BlockSplitRequest(BaseModel):
    split_line_wkt: str  # WKT LineString (EPSG:4326) cắt Block
    new_block_codes: Optional[List[str]] = None  # Tên/Mã mới cho các lô con sau khi tách


class UndoSplitRequest(BaseModel):
    """Request body để hoàn tác thao tác tách lô gần nhất."""
    parent_block_id: int  # ID của lô cha cần phục hồi


class UndoSplitResponse(BaseModel):
    """Response trả về sau khi hoàn tác tách lô thành công."""
    restored_block: BlockResponse  # Lô cha đã được phục hồi (status='active')
    deleted_child_ids: List[int]  # Danh sách ID các lô con đã bị xóa
