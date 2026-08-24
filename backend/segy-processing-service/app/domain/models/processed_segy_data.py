from dataclasses import dataclass, field

from app.domain.models.line import Line
from app.domain.models.line_string import LineString
from app.domain.models.line_topology import (
    LineTopologyAnalysis,
)
from app.domain.models.processed_line import ProcessedLine
from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.shot_point_analysis import (
    ShotPointAnalysis,
)
from app.domain.models.trace import ProcessedTrace


@dataclass
class ProcessedSegyData:
    """
    Result of processing a SEG-Y file.

    This model represents the complete application-level
    processing result before persistence to PostgreSQL/PostGIS.
    """

    metadata: SegyMetadata

    processed_traces: list[ProcessedTrace] = field(
        default_factory=list
    )

    shot_point_analysis: ShotPointAnalysis | None = None

    line: Line | None = None

    topology_analysis: LineTopologyAnalysis | None = None

    wgs84_geometry: LineString | None = None

    lines: list[ProcessedLine] = field(default_factory=list)
