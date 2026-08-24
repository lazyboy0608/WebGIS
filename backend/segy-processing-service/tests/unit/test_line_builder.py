from app.domain.models.coordinate import Coordinate
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.line_builder import LineBuilder


def create_trace(
    index: int,
    shot_point: int,
    x: float,
    y: float,
) -> ProcessedTrace:

    return ProcessedTrace(
        trace_index=index,
        source_point=SourcePoint(
            number=shot_point
        ),
        coordinate=Coordinate(
            x=x,
            y=y,
        ),
        samples=None,
    )


def test_build_continuous_line() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 20, 0),
    ]

    builder = LineBuilder()

    result = builder.build(traces)

    assert result is not None

    assert len(result.coordinates) == 3
    assert len(result.trace_indices) == 3
    assert len(result.shot_points) == 3


def test_build_line_preserves_trace_order() -> None:

    traces = [
        create_trace(5, 105, 50, 0),
        create_trace(6, 106, 60, 0),
        create_trace(7, 107, 70, 0),
    ]

    builder = LineBuilder()

    result = builder.build(traces)

    assert result.trace_indices == [
        5,
        6,
        7,
    ]

    assert result.shot_points == [
        105,
        106,
        107,
    ]


def test_build_line_preserves_coordinates() -> None:

    traces = [
        create_trace(0, 100, 0, 10),
        create_trace(1, 101, 20, 30),
        create_trace(2, 102, 40, 50),
    ]

    builder = LineBuilder()

    result = builder.build(traces)

    assert result.coordinates == [
        Coordinate(x=0, y=10),
        Coordinate(x=20, y=30),
        Coordinate(x=40, y=50),
    ]


def test_build_empty_line() -> None:

    builder = LineBuilder()

    result = builder.build([])

    assert result.coordinates == []
    assert result.trace_indices == []
    assert result.shot_points == []


def test_build_line_with_repeated_shot_point() -> None:

    traces = [
        create_trace(0, 153, 0, 0),
        create_trace(1, 153, 10, 0),
        create_trace(2, 154, 20, 0),
    ]

    builder = LineBuilder()

    result = builder.build(traces)

    assert result.shot_points == [
        153,
        153,
        154,
    ]

    assert len(result.coordinates) == 3