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
    task_id: str | None = None
    points: list["ProcessedPointResponse"] = Field(default_factory=list)


class SegyUploadBatchResponse(BaseModel):
    """Results returned after processing multiple uploaded SEG-Y files."""

    files: list[SegyProcessingResponse]


class SegyBatchDeleteRequest(BaseModel):
    """Request schema for batch deleting SEG-Y files."""

    ids: list[int] = Field(..., description="List of SEG-Y file IDs to delete")


class SegyBatchDeleteResponse(BaseModel):
    """Response schema after batch deleting SEG-Y files."""

    deleted_ids: list[int]
    count: int


class ProcessedPointResponse(BaseModel):
    """A processed trace coordinate ready for a WebGIS client."""

    trace_index: int
    shot_point: int | None
    x: float
    y: float
    srid: int = 4326


class SegyTaskStatusResponse(BaseModel):
    """Status of an asynchronous SEG-Y upload and processing task."""

    task_id: str
    filename: str
    status: str
    progress_percent: int
    message: str
    result: object | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SegyParsedHeaderDetails(BaseModel):
    """Structured details parsed from SEG-Y textual header."""
    survey: str | None = None
    line_id: str | None = None
    client: str | None = None
    contractor: str | None = None
    datum: str | None = None
    ellipsoid: str | None = None
    projection: str | None = None
    zone: int | None = None
    scale_factor: float | None = None
    central_meridian: str | None = None
    false_easting: float | None = None
    false_northing: float | None = None
    units: str | None = None


class SegySampleTrace(BaseModel):
    """Initial trace inspection data showing SAC, SAED and coordinates."""
    trace_index: int
    trace_sequence_line: int | None = None
    sac: int | None = None
    saed: int | None = None
    effective_scalar: int = 1
    source_x: float | None = None
    source_y: float | None = None
    cdp_x: float | None = None
    cdp_y: float | None = None
    scaled_x: float | None = None
    scaled_y: float | None = None


class SegyHeaderInspectionResponse(BaseModel):
    """Result of pre-inspecting SEG-Y textual/binary headers."""

    filename: str
    source_crs: str
    source_crs_name: str
    default_target_crs: str = "EPSG:4326"
    default_target_crs_name: str = "WGS 84 (Kinh độ / Vĩ độ - EPSG:4326)"
    trace_count: int = 0
    textual_header_preview: str | None = None
    header_details: SegyParsedHeaderDetails | None = None
    sample_traces: list[SegySampleTrace] | None = None


class CrsPresetResponse(BaseModel):
    """A CRS preset option for users to select."""

    code: str
    name: str
    description: str | None = None
    category: str | None = None


