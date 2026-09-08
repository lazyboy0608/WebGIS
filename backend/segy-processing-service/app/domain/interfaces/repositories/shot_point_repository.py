from abc import ABC, abstractmethod

from app.domain.models.seismic_shot_point import SeismicShotPoint
# from app.domain.models.shot_point import ShotPoint


class ShotPointRepository(ABC):
    """Repository contract for seismic shot points."""

    @abstractmethod
    def save_shot_point(
        self,
        shot_point: SeismicShotPoint,
        segy_file_id: int,
        seismic_line_id: int | None = None,
    ) -> SeismicShotPoint:
        raise NotImplementedError

    def save_shot_points_bulk(
        self,
        shot_points: list[tuple[SeismicShotPoint, int | None]],
        segy_file_id: int,
    ) -> dict[tuple[int | None, int], int]:
        """Default fallback implementation iterating over save_shot_point."""
        result_map: dict[tuple[int | None, int], int] = {}
        for shot_point, line_id in shot_points:
            saved = self.save_shot_point(shot_point, segy_file_id, line_id)
            if saved.id is None:
                raise ValueError(
                    f"Persisted Shot Point {shot_point.number} "
                    "does not have a database ID"
                )
            result_map[(line_id, shot_point.number)] = saved.id
        return result_map