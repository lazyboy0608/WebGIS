from app.domain.models.coordinate import Coordinate
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.line_topology_analyzer import (
    LineTopologyAnalyzer,
)


def create_trace(
    index: int,
    sp: int,
    x: float,
    y: float,
) -> ProcessedTrace:

    return ProcessedTrace(
        trace_index=index,
        source_point=SourcePoint(
            number=sp
        ),
        coordinate=Coordinate(
            x=x,
            y=y,
        ),
    )


def test_continuous_line() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 20, 0),
        create_trace(3, 103, 30, 0),
    ]

    analyzer = LineTopologyAnalyzer(
        gap_threshold=15
    )

    result = analyzer.analyze(traces)

    assert result.trace_count == 4
    assert result.coordinate_count == 4
    assert result.distance_count == 3

    assert result.minimum_distance == 10
    assert result.maximum_distance == 10
    assert result.average_distance == 10
    assert result.median_distance == 10

    assert result.gap_count == 0
    assert result.reversed_segment_count == 0
    assert result.monotonic_shot_point is True
    assert result.continuous is True

def test_detect_gap() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 100, 0),
    ]

    analyzer = LineTopologyAnalyzer(
        gap_threshold=20
    )

    result = analyzer.analyze(traces)

    assert result.gap_count == 1
    assert result.maximum_distance == 90
    assert result.continuous is False

def test_detect_reversed_segment() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 5, 0),
    ]

    analyzer = LineTopologyAnalyzer()

    result = analyzer.analyze(traces)

    assert result.reversed_segment_count == 1
    assert result.continuous is False

def test_non_monotonic_shot_points() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 99, 20, 0),
    ]

    analyzer = LineTopologyAnalyzer()

    result = analyzer.analyze(traces)

    assert result.monotonic_shot_point is False
    assert result.continuous is False

def test_empty_traces() -> None:

    analyzer = LineTopologyAnalyzer()

    result = analyzer.analyze([])

    assert result.trace_count == 0
    assert result.coordinate_count == 0
    assert result.distance_count == 0

    assert result.minimum_distance is None
    assert result.maximum_distance is None
    assert result.average_distance is None
    assert result.median_distance is None

    assert result.continuous is True