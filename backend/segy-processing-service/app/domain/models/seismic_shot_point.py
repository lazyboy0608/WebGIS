from dataclasses import dataclass, field

from app.domain.models.coordinate import Coordinate


@dataclass
class SeismicShotPoint:
    """
    Represents a persisted seismic Shot Point.
    """

    number: int

    trace_indices: list[int] = field(
        default_factory=list
    )

    coordinates: list[Coordinate] = field(
        default_factory=list
    )

    id: int | None = None