from dataclasses import dataclass
from typing import Any, Sequence

from app.domain.models.coordinate import Coordinate


@dataclass(frozen=True)
class Trace:
    """
    Raw trace representation returned by the SEG-Y reader.

    This model represents data before application-level
    processing.
    """

    index: int
    header: Any
    samples: Sequence[float] | None = None


@dataclass(frozen=True)
class SourcePoint:
    """
    Seismic source point associated with a trace.
    """

    number: int | None


@dataclass(frozen=True)
class ProcessedTrace:
    """
    Application-level representation of a processed SEG-Y trace.
    """

    trace_index: int

    source_point: SourcePoint

    coordinate: Coordinate

    samples: Sequence[float] | None = None

    wgs84_coordinate: Coordinate | None = None

    line_group_key: str | None = None
