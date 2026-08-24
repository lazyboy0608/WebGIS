from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SegyFileCreate(BaseModel):
    """Request schema for creating a SEG-Y file record."""

    filename: str
    file_path: str
    file_size: int
    source_crs: str
    trace_count: int
    line_count: int
    geometry: object | None = None


class SegyFileUpdate(BaseModel):
    """Request schema for updating a SEG-Y file record."""

    filename: str
    file_path: str
    file_size: int
    source_crs: str
    trace_count: int
    line_count: int
    geometry: object | None = None


class SegyFileResponse(BaseModel):
    """Response schema for a SEG-Y file."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: str
    file_size: int
    source_crs: str
    trace_count: int
    line_count: int
    geometry: object | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SegyProcessingResponse(BaseModel):
    """Summary returned after processing and persisting a SEG-Y file."""

    segy_file_id: int
    filename: str
    trace_count: int
    shot_point_count: int
    line_point_count: int
    line_count: int = 1
    topology_continuous: bool
    geometry_srid: int | None = None
    points: list["ProcessedPointResponse"] = Field(default_factory=list)


class SegyUploadBatchResponse(BaseModel):
    """Results returned after processing multiple uploaded SEG-Y files."""

    files: list[SegyProcessingResponse]


class ProcessedPointResponse(BaseModel):
    """A processed trace coordinate ready for a WebGIS client."""

    trace_index: int
    shot_point: int | None
    x: float
    y: float
    srid: int = 4326
