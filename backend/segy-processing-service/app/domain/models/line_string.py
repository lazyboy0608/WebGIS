from dataclasses import dataclass

from app.domain.models.coordinate import Coordinate


@dataclass(frozen=True)
class LineString:
    """
    Represents a GIS LineString geometry.

    Coordinates are expected to be in WGS84.
    """

    coordinates: list[Coordinate]

    srid: int = 4326