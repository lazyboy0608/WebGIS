from dataclasses import dataclass, field

from app.domain.models.coordinate import Coordinate


@dataclass(frozen=True)
class Line:
    """
    Represents a seismic line built from processed traces.
    """

    coordinates: list[Coordinate] = field(
        default_factory=list
    )

    trace_indices: list[int] = field(
        default_factory=list
    )

    shot_points: list[int] = field(
        default_factory=list
    )