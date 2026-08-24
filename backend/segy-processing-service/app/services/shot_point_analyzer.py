from collections.abc import Iterable

from app.domain.models.shot_point import ShotPoint
from app.domain.models.shot_point_analysis import (
    ShotPointAnalysis,
)
from app.domain.models.trace import Trace
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)


class ShotPointAnalyzer:
    """
    Analyze traces and group them by Shot Point.
    """

    def __init__(
        self,
        coordinate_transformer: CoordinateTransformer,
    ) -> None:
        self._coordinate_transformer = (
            coordinate_transformer
        )

    def analyze(
        self,
        traces: Iterable[Trace],
    ) -> ShotPointAnalysis:

        shot_points: dict[tuple[str, int], ShotPoint] = {}

        total_trace_count = 0
        missing_shot_point_count = 0

        for trace in traces:
            total_trace_count += 1

            sp = trace.header.energy_source_point

            if sp is None or sp == 0:
                missing_shot_point_count += 1
                continue

            line_key = (
                str(trace.header.original_field_record_number)
                if trace.header.original_field_record_number is not None
                else "default"
            )
            shot_point_key = (line_key, sp)
            if shot_point_key not in shot_points:
                shot_points[shot_point_key] = ShotPoint(
                    number=sp,
                    line_group_key=line_key,
                )

            shot_point = shot_points[shot_point_key]

            shot_point.trace_indices.append(
                trace.index
            )

            coordinate = (
                self._coordinate_transformer.transform(
                    x=trace.header.source_x,
                    y=trace.header.source_y,
                    scalar=trace.header.coordinate_scalar,
                    coordinate_units=(
                        trace.header.coordinate_units
                    ),
                )
            )

            shot_point.coordinates.append(
                coordinate
            )

        ordered_shot_points = sorted(
            shot_points.values(),
            key=lambda shot_point: (
                shot_point.line_group_key or "default",
                shot_point.number,
            ),
        )

        return ShotPointAnalysis(
            total_trace_count=total_trace_count,
            unique_shot_point_count=len(
                ordered_shot_points
            ),
            shot_points=ordered_shot_points,
            missing_shot_point_count=(
                missing_shot_point_count
            ),
        )
