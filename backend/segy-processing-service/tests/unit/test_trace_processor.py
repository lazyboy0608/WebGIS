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
    elevation_scalar: int = 1

    @property
    def effective_coordinate_scalar(self) -> int:
        if self.coordinate_scalar is not None and self.coordinate_scalar not in (0, 1):
            return self.coordinate_scalar
        if self.elevation_scalar is not None and self.elevation_scalar not in (0, 1):
            return self.elevation_scalar
        return 1


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


def test_process_trace_fallback_coordinates() -> None:
    processor = create_processor()

    @dataclass
    class FallbackHeader:
        energy_source_point: int = 1
        source_x: int = 0
        source_y: int = 0
        cdp_x: int = 500000
        cdp_y: int = 1100000
        group_x: int = 0
        group_y: int = 0
        coordinate_scalar: int = 1
        coordinate_units: int = 0

    trace = FakeTrace(
        index=0,
        header=FallbackHeader(),
    )

    result = processor.process(trace)
    assert result.coordinate.x == 500000
    assert result.coordinate.y == 1100000


def test_process_trace_falls_back_to_elevation_scalar_saed() -> None:
    processor = create_processor()

    trace = FakeTrace(
        index=0,
        header=FakeHeader(
            energy_source_point=1,
            source_x=22440238,
            source_y=88800263,
            coordinate_scalar=1,  # SAC is 1 (unscaled)
            elevation_scalar=-100,  # SAED is -100 (Image 2 case)
            coordinate_units=0,
        ),
    )

    result = processor.process(trace)
    assert result.coordinate.x == 224402.38
    assert result.coordinate.y == 888002.63