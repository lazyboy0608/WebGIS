from dataclasses import dataclass, field

from app.domain.models.coordinate import Coordinate


@dataclass(slots=True)
class SeismicLine:

    line_id: str = ""

    coordinates: list[Coordinate] = field(
        default_factory=list
    )

    id: int | None = None

    @property
    def point_count(self) -> int:
        return len(self.coordinates)

    def add_coordinate(
        self,
        coordinate: Coordinate,
    ) -> None:
        self.coordinates.append(coordinate)