from collections.abc import Iterable
from math import hypot

from app.domain.models.line_topology import (
    LineTopologyAnalysis,
)
from app.domain.models.trace import (
    ProcessedTrace,
)


class LineTopologyAnalyzer:
    """
    Analyze spatial continuity and ordering of
    processed seismic traces.
    """

    def __init__(
        self,
        gap_threshold: float = 50.0,
    ) -> None:
        self._gap_threshold = gap_threshold

    def analyze(
        self,
        traces: Iterable[ProcessedTrace],
    ) -> LineTopologyAnalysis:

        trace_list = list(traces)

        if not trace_list:
            return LineTopologyAnalysis(
                trace_count=0,
                coordinate_count=0,
                distance_count=0,
                minimum_distance=None,
                maximum_distance=None,
                average_distance=None,
                median_distance=None,
                gap_count=0,
                maximum_gap=None,
                reversed_segment_count=0,
                monotonic_shot_point=True,
                continuous=True,
                start_coordinate=None,
                end_coordinate=None,
            )

        coordinates = [
            trace.coordinate
            for trace in trace_list
        ]

        distances = self._calculate_distances(
            coordinates
        )

        shot_points = [
            trace.source_point.number
            for trace in trace_list
            if trace.source_point.number is not None
        ]

        monotonic_shot_point = (
            self._is_monotonic(shot_points)
        )

        gap_count = self._count_gaps(
            distances
        )

        reversed_segment_count = (
            self._count_reversed_segments(
                coordinates
            )
        )

        minimum_distance = (
            min(distances)
            if distances
            else None
        )

        maximum_distance = (
            max(distances)
            if distances
            else None
        )

        average_distance = (
            sum(distances) / len(distances)
            if distances
            else None
        )

        median_distance = (
            self._median(distances)
            if distances
            else None
        )

        gaps = [
            distance
            for distance in distances
            if distance > self._gap_threshold
        ]

        maximum_gap = (
            max(gaps)
            if gaps
            else None
        )

        continuous = (
            gap_count == 0
            and reversed_segment_count == 0
            and monotonic_shot_point
        )

        return LineTopologyAnalysis(
            trace_count=len(trace_list),
            coordinate_count=len(coordinates),
            distance_count=len(distances),
            minimum_distance=minimum_distance,
            maximum_distance=maximum_distance,
            average_distance=average_distance,
            median_distance=median_distance,
            gap_count=gap_count,
            maximum_gap=maximum_gap,
            reversed_segment_count=(
                reversed_segment_count
            ),
            monotonic_shot_point=(
                monotonic_shot_point
            ),
            continuous=continuous,
            start_coordinate=coordinates[0],
            end_coordinate=coordinates[-1],
        )

    @staticmethod
    def _calculate_distances(
        coordinates,
    ) -> list[float]:

        distances: list[float] = []

        for previous, current in zip(
            coordinates,
            coordinates[1:],
        ):
            distance = hypot(
                current.x - previous.x,
                current.y - previous.y,
            )

            distances.append(distance)

        return distances

    @staticmethod
    def _is_monotonic(
        values: list[int],
    ) -> bool:

        if len(values) < 2:
            return True

        increasing = all(
            current >= previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )

        decreasing = all(
            current <= previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )

        return increasing or decreasing

    def _count_gaps(
        self,
        distances: list[float],
    ) -> int:

        if self._gap_threshold is None:
            return 0

        return sum(
            1
            for distance in distances
            if distance > self._gap_threshold
        )

    @staticmethod
    def _count_reversed_segments(
        coordinates,
    ) -> int:

        if len(coordinates) < 3:
            return 0

        reversed_count = 0

        previous_dx = (
            coordinates[1].x
            - coordinates[0].x
        )

        previous_dy = (
            coordinates[1].y
            - coordinates[0].y
        )

        for index in range(
            1,
            len(coordinates) - 1,
        ):
            current_dx = (
                coordinates[index + 1].x
                - coordinates[index].x
            )

            current_dy = (
                coordinates[index + 1].y
                - coordinates[index].y
            )

            dot_product = (
                previous_dx * current_dx
                + previous_dy * current_dy
            )

            if dot_product < 0:
                reversed_count += 1

            previous_dx = current_dx
            previous_dy = current_dy

        return reversed_count

    @staticmethod
    def _median(
        values: list[float],
    ) -> float:

        ordered = sorted(values)

        middle = len(ordered) // 2

        if len(ordered) % 2 == 1:
            return ordered[middle]

        return (
            ordered[middle - 1]
            + ordered[middle]
        ) / 2