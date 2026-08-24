from dataclasses import dataclass, field

from app.domain.models.coordinate import Coordinate


@dataclass
class ShotPoint:
    """
    Represents a seismic Shot Point.

    A Shot Point may contain one or more traces.
    """

    number: int

    trace_indices: list[int] = field(
        default_factory=list
    )

    coordinates: list[Coordinate] = field(
        default_factory=list
    )

    wgs84_coordinates: list[Coordinate] = field(
        default_factory=list
    )

    line_group_key: str | None = None