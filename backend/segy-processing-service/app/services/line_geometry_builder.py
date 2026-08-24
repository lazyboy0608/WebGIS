from collections.abc import Iterable

from app.domain.models.line import Line
from app.domain.models.trace import ProcessedTrace


class LineGeometryBuilder:
    """
    Builds a seismic Line from processed traces.

    The builder preserves the input trace order.
    """

    def build(
        self,
        traces: Iterable[ProcessedTrace],
    ) -> Line:

        trace_list = list(traces)

        coordinates = [
            trace.coordinate
            for trace in trace_list
        ]

        trace_indices = [
            trace.trace_index
            for trace in trace_list
        ]

        shot_points = [
            trace.source_point.number
            for trace in trace_list
            if trace.source_point.number is not None
        ]

        return Line(
            coordinates=coordinates,
            trace_indices=trace_indices,
            shot_points=shot_points,
        )