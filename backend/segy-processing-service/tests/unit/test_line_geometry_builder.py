from app.domain.models.coordinate import Coordinate
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.line_geometry_builder import (
    LineGeometryBuilder,
)


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


def test_build_line() -> None:

    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 20, 0),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert len(result.coordinates) == 3

    assert result.trace_indices == [
        0,
        1,
        2,
    ]

    assert result.shot_points == [
        100,
        101,
        102,
    ]


def test_build_line_preserves_coordinates() -> None:

    traces = [
        create_trace(0, 100, 10, 20),
        create_trace(1, 101, 30, 40),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert result.coordinates[0].x == 10
    assert result.coordinates[0].y == 20

    assert result.coordinates[1].x == 30
    assert result.coordinates[1].y == 40


def test_build_empty_line() -> None:

    builder = LineGeometryBuilder()

    result = builder.build([])

    assert result.coordinates == []
    assert result.trace_indices == []
    assert result.shot_points == []


def test_build_line_with_missing_shot_point() -> None:

    traces = [
        ProcessedTrace(
            trace_index=0,
            source_point=SourcePoint(
                number=100
            ),
            coordinate=Coordinate(
                x=0,
                y=0,
            ),
        ),
        ProcessedTrace(
            trace_index=1,
            source_point=SourcePoint(
                number=None
            ),
            coordinate=Coordinate(
                x=10,
                y=0,
            ),
        ),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert result.trace_indices == [
        0,
        1,
    ]

    assert result.shot_points == [
        100,
    ]

    assert len(result.coordinates) == 2

def test_line_keeps_coordinate_trace_alignment() -> None:
    traces = [
        create_trace(0, 100, 0, 0),
        create_trace(1, 101, 10, 0),
        create_trace(2, 102, 20, 0),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert len(result.coordinates) == len(
        result.trace_indices
    )

    for coordinate, trace_index in zip(
        result.coordinates,
        result.trace_indices,
    ):
        assert coordinate == traces[trace_index].coordinate

def test_builder_does_not_reorder_traces() -> None:
    traces = [
        create_trace(5, 105, 50, 0),
        create_trace(3, 103, 30, 0),
        create_trace(4, 104, 40, 0),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert result.trace_indices == [5, 3, 4]

    assert result.coordinates == [
        traces[0].coordinate,
        traces[1].coordinate,
        traces[2].coordinate,
    ]

def test_builder_preserves_duplicate_coordinates() -> None:
    traces = [
        create_trace(0, 100, 100, 200),
        create_trace(1, 101, 100, 200),
        create_trace(2, 102, 110, 200),
    ]

    builder = LineGeometryBuilder()

    result = builder.build(traces)

    assert result.coordinates == [
        traces[0].coordinate,
        traces[1].coordinate,
        traces[2].coordinate,
    ]