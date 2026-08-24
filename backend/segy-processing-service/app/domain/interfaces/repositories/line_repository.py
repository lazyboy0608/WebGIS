from abc import ABC, abstractmethod

from app.domain.models.seismic_line import SeismicLine


class LineRepository(ABC):
    """Repository contract for seismic lines."""

    @abstractmethod
    def save_line(
        self,
        line: SeismicLine,
        segy_file_id: int,
    ) -> SeismicLine:
        raise NotImplementedError