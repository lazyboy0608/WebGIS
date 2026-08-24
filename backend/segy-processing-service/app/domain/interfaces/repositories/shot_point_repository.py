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