from collections.abc import Iterable

from app.domain.models.trace import Trace
from app.domain.models.trace_header import TraceHeader
from app.domain.models.trace_header_profile import (
    FieldStatistics,
    TraceHeaderProfile,
)


class TraceHeaderProfiler:
    """
    Profiles SEG-Y trace header fields.

    This service does not modify traces.
    It only analyzes header values.
    """

    PROFILE_FIELDS = (
        "trace_sequence_number",
        "trace_sequence_number_within_line",
        "original_field_record_number",
        "trace_number_within_field_record",
        "energy_source_point",
        "cdp_ensemble_number",
        "cdp_trace_number",
        "source_x",
        "source_y",
        "coordinate_scalar",
        "coordinate_units",
    )

    def profile(
        self,
        traces: Iterable[Trace],
    ) -> TraceHeaderProfile:

        statistics = {
            field_name: FieldStatistics(
                field_name=field_name,
            )
            for field_name in self.PROFILE_FIELDS
        }

        trace_count = 0

        for trace in traces:
            trace_count += 1

            self._process_header(
                trace.header,
                statistics,
            )

        for field_statistics in statistics.values():
            field_statistics.unique_count = len(
                field_statistics.values
            )

        return TraceHeaderProfile(
            trace_count=trace_count,
            fields=statistics,
        )

    def _process_header(
        self,
        header: TraceHeader,
        statistics: dict[str, FieldStatistics],
    ) -> None:

        for field_name in self.PROFILE_FIELDS:
            value = getattr(
                header,
                field_name,
                None,
            )

            field_statistics = statistics[
                field_name
            ]

            field_statistics.total_count += 1

            if value is None:
                field_statistics.missing_count += 1
                continue

            field_statistics.values[value] = (
                field_statistics.values.get(
                    value,
                    0,
                )
                + 1
            )

            if (
                field_statistics.minimum is None
                or value < field_statistics.minimum
            ):
                field_statistics.minimum = value

            if (
                field_statistics.maximum is None
                or value > field_statistics.maximum
            ):
                field_statistics.maximum = value