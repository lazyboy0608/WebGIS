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
