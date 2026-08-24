from dataclasses import dataclass

from app.domain.models.coordinate import Coordinate


@dataclass(frozen=True)
class LineTopologyAnalysis:
    """
    Result of analyzing the spatial and sequential
    topology of seismic traces.
    """

    trace_count: int

    coordinate_count: int

    distance_count: int

    minimum_distance: float | None

    maximum_distance: float | None

    average_distance: float | None

    median_distance: float | None

    maximum_gap: float | None

    gap_count: int

    reversed_segment_count: int

    monotonic_shot_point: bool

    continuous: bool

    start_coordinate: Coordinate | None

    end_coordinate: Coordinate | None