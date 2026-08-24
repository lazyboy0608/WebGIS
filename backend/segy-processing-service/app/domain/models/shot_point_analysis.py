from dataclasses import dataclass, field

from app.domain.models.shot_point import ShotPoint


@dataclass
class ShotPointAnalysis:
    """
    Result of Shot Point analysis.
    """

    total_trace_count: int

    unique_shot_point_count: int

    shot_points: list[ShotPoint] = field(
        default_factory=list
    )

    missing_shot_point_count: int = 0

    @property
    def min_shot_point(self) -> int | None:
        if not self.shot_points:
            return None

        return self.shot_points[0].number

    @property
    def max_shot_point(self) -> int | None:
        if not self.shot_points:
            return None

        return self.shot_points[-1].number