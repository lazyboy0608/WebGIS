from dataclasses import dataclass

from app.domain.models.coordinate import (
    CoordinateUnit,
)
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)
from app.services.trace_processor import (
    TraceProcessor,
)


@dataclass
class FakeHeader:
    energy_source_point: int
    source_x: int
    source_y: int
    coordinate_scalar: int
    coordinate_units: int


@dataclass
class FakeTrace:
    index: int
    header: FakeHeader
    samples: list[float] | None = None


def create_processor() -> TraceProcessor:
    transformer = CoordinateTransformer()

    return TraceProcessor(
        coordinate_transformer=transformer
    )


def test_process_trace() -> None:
    processor = create_processor()

    trace = FakeTrace(
        index=0,
        header=FakeHeader(
            energy_source_point=153,
            source_x=1610154,
            source_y=-191584,
            coordinate_scalar=1,
            coordinate_units=0,
        ),
    )

    result = processor.process(trace)

    assert result.trace_index == 0

    assert (
        result.source_point.number
        == 153
    )

    assert result.coordinate.x == 1610154

    assert result.coordinate.y == -191584

    assert (
        result.coordinate.units
        == CoordinateUnit.UNKNOWN
    )

    assert result.samples is None


def test_process_trace_with_samples() -> None:
    processor = create_processor()

    trace = FakeTrace(
        index=10,
        header=FakeHeader(
            energy_source_point=160,
            source_x=1610154,
            source_y=-191000,
            coordinate_scalar=1,
            coordinate_units=0,
        ),
        samples=[
            1.0,
            2.0,
            3.0,
        ],
    )

    result = processor.process(trace)

    assert result.trace_index == 10

    assert (
        result.source_point.number
        == 160
    )

    assert result.samples == [
        1.0,
        2.0,
        3.0,
    ]


def test_process_trace_applies_scalar() -> None:
    processor = create_processor()

    trace = FakeTrace(
        index=1,
        header=FakeHeader(
            energy_source_point=154,
            source_x=100,
            source_y=200,
            coordinate_scalar=10,
            coordinate_units=0,
        ),
    )

    result = processor.process(trace)

    assert result.coordinate.x == 1000

    assert result.coordinate.y == 2000