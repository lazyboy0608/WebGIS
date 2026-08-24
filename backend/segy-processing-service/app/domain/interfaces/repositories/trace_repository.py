from abc import ABC, abstractmethod

from app.domain.models.trace import ProcessedTrace
from app.domain.models.seismic_trace import SeismicTrace

class TraceRepository(ABC):
    """Repository contract for seismic traces."""

    @abstractmethod
    def save_trace(
        self,
        trace: ProcessedTrace,
        segy_file_id: int,
        seismic_line_id: int | None = None,
        shot_point_id: int | None = None,
    ) -> SeismicTrace:
        raise NotImplementedError