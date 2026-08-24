from collections.abc import Iterable

from app.domain.models.line import Line
from app.domain.models.trace import ProcessedTrace


class LineBuilder:
    """
    Builds a seismic line from processed traces.
    """

    def build(
        self,
        traces: Iterable[ProcessedTrace],
    ) -> Line:

        trace_list = list(traces)

        return Line(
            coordinates=[
                trace.coordinate
                for trace in trace_list
            ],
            trace_indices=[
                trace.trace_index
                for trace in trace_list
            ],
            shot_points=[
                trace.source_point.number
                for trace in trace_list
            ],
        )

    def build_grouped(
        self,
        traces: Iterable[ProcessedTrace],
    ) -> dict[str, Line]:
        grouped: dict[str, list[ProcessedTrace]] = {}
        for trace in traces:
            key = trace.line_group_key or "default"
            grouped.setdefault(key, []).append(trace)

        return {
            key: self.build(grouped_traces)
            for key, grouped_traces in grouped.items()
        }
