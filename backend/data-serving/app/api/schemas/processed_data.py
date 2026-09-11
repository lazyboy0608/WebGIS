from typing import Any

from pydantic import BaseModel, Field


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature] = Field(default_factory=list)


class ProcessedDataSummary(BaseModel):
    id: int
    filename: str
    source_crs: str
    trace_count: int
    line_count: int
    processed_line_count: int
    processed_shot_point_count: int
    processed_trace_count: int


class FileListItem(BaseModel):
    id: int
    filename: str
    source_crs: str
    trace_count: int
    line_count: int
    processed_line_count: int
    processed_shot_point_count: int
    processed_trace_count: int
    has_processed_data: bool = True


class FileListResponse(BaseModel):
    items: list[FileListItem] = Field(default_factory=list)
    total: int
    offset: int = 0
    limit: int = 50


class ExportCsvResponse(BaseModel):
    segy_file_id: int
    filename: str
    object_name: str
    bucket: str
    size_bytes: int
    record_count: int
    download_url: str


class BatchExportRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, description="List of SEG-Y file IDs to export")


class BatchExportCsvResponse(BaseModel):
    results: list[ExportCsvResponse] = Field(default_factory=list)
    total: int


class DownloadUrlResponse(BaseModel):
    segy_file_id: int
    filename: str
    object_name: str
    bucket: str
    download_url: str


class ExportSegyPolygonRequest(BaseModel):
    polygon_ring: list[list[float]] = Field(..., description="Array of [lon, lat] points forming closed ring")
    polygon_name: str = Field(default="spatial_filter", description="Name of the polygon filter")
    file_ids: list[int] | None = Field(default=None, description="Optional filter by file IDs")
    target_crs: str | None = Field(default=None, description="Optional target CRS to export (e.g. EPSG:3405)")


class ExportSegyResult(BaseModel):
    segy_file_id: int
    line_id: str
    filename: str
    object_name: str
    bucket: str
    size_bytes: int
    trace_count: int
    download_url: str


class BatchExportSegyResponse(BaseModel):
    results: list[ExportSegyResult] = Field(default_factory=list)
    total: int


class BatchClipLinesRequest(BaseModel):
    file_ids: list[int] = Field(..., min_length=1, description="List of SEG-Y file IDs to clip")
    polygon_rings: list[list[list[float]]] = Field(..., min_length=1, description="Array of polygon rings [[[lon, lat], ...], ...]")


class BatchClipLinesResponse(BaseModel):
    inside: GeoJSONFeatureCollection
    outside: GeoJSONFeatureCollection


