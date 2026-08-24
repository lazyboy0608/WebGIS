from dataclasses import dataclass

from app.domain.models.coordinate import Coordinate


@dataclass
class SeismicTrace:
    """
    Represents a processed seismic trace
    prepared for persistence.
    """

    trace_index: int = 0

    shot_point: int | None = None

    coordinate: Coordinate | None = None

    id: int | None = None