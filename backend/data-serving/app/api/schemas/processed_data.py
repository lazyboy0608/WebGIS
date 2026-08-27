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


class DownloadUrlResponse(BaseModel):
    segy_file_id: int
    filename: str
    object_name: str
    bucket: str
    download_url: str

