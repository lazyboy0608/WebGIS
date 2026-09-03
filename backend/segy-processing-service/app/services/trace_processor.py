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

        x = getattr(header, "source_x", None) or 0
        y = getattr(header, "source_y", None) or 0

        if x == 0 and y == 0:
            cdp_x = getattr(header, "cdp_x", None) or 0
            cdp_y = getattr(header, "cdp_y", None) or 0
            if cdp_x != 0 or cdp_y != 0:
                x, y = cdp_x, cdp_y
            else:
                group_x = getattr(header, "group_x", None) or 0
                group_y = getattr(header, "group_y", None) or 0
                if group_x != 0 or group_y != 0:
                    x, y = group_x, group_y

        units = getattr(header, "coordinate_units", 1)
        if units is None:
            units = 1

        scalar = getattr(header, "coordinate_scalar", 1)
        if scalar is None:
            scalar = 1

        coordinate = (
            self._coordinate_transformer.transform(
                x=x,
                y=y,
                scalar=scalar,
                coordinate_units=units,
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
