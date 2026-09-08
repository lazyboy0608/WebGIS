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

    def save_traces_bulk(
        self,
        traces: list[tuple[ProcessedTrace, int | None, int | None]],
        segy_file_id: int,
    ) -> None:
        """Default fallback implementation iterating over save_trace."""
        for trace, line_id, shot_point_id in traces:
            self.save_trace(trace, segy_file_id, line_id, shot_point_id)