from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class BlockInfo(BaseModel):
    id: int
    block_code: str
    operator: Optional[str] = None
    basin_name: Optional[str] = None
    area_km2: Optional[float] = None
    status: str
    parent_id: Optional[int] = None
    source_file: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BlockUploadResponse(BaseModel):
    message: str
    imported_count: int
    blocks: List[BlockInfo]
