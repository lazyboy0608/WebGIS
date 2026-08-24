from collections.abc import Iterable, Iterator

from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)


class TraceProcessor:
    """
    Convert raw SEG-Y traces into application-level
    ProcessedTrace objects.
    """

    def __init__(
        self,
        coordinate_transformer: CoordinateTransformer,
    ) -> None:

        self._coordinate_transformer = (
            coordinate_transformer
        )

    def process(self, trace) -> ProcessedTrace:
        """
        Process a single SEG-Y trace.
        """

        header = trace.header

        coordinate = (
            self._coordinate_transformer.transform(
                x=header.source_x,
                y=header.source_y,
                scalar=header.coordinate_scalar,
                coordinate_units=header.coordinate_units,
            )
        )

        source_point = SourcePoint(
            number=header.energy_source_point
        )

        samples = (
            trace.samples
            if trace.samples is not None
            else None
        )

        return ProcessedTrace(
            trace_index=trace.index,
            source_point=source_point,
            coordinate=coordinate,
            samples=samples,
            line_group_key=self._line_group_key(trace),
        )

    @staticmethod
    def _line_group_key(trace) -> str | None:
        value = getattr(
            trace.header,
            "original_field_record_number",
            None,
        )
        return None if value is None else str(value)

    def process_many(
        self,
        traces: Iterable,
    ) -> Iterator[ProcessedTrace]:
        """
        Process traces lazily.

        Traces are not accumulated in memory.
        """

        for trace in traces:
            yield self.process(trace)
