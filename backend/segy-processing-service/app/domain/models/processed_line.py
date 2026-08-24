from dataclasses import dataclass

from app.domain.models.line import Line
from app.domain.models.line_string import LineString
from app.domain.models.line_topology import LineTopologyAnalysis


@dataclass
class ProcessedLine:
    """One grouped and transformed seismic line."""

    line_key: str
    line: Line
    wgs84_geometry: LineString
    topology_analysis: LineTopologyAnalysis
