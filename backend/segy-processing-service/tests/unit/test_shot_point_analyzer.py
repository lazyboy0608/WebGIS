from app.domain.models.trace import Trace
from app.domain.models.trace_header import TraceHeader
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)
from app.services.shot_point_analyzer import (
    ShotPointAnalyzer,
)


def test_group_traces_by_shot_point() -> None:

    transformer = CoordinateTransformer()

    analyzer = ShotPointAnalyzer(
        coordinate_transformer=transformer
    )

    traces = [
        Trace(
            index=0,
            header=TraceHeader(
                energy_source_point=100,
                source_x=1000,
                source_y=2000,
                coordinate_scalar=1,
                coordinate_units=1,
            ),
        ),
        Trace(
            index=1,
            header=TraceHeader(
                energy_source_point=100,
                source_x=1100,
                source_y=2100,
                coordinate_scalar=1,
                coordinate_units=1,
            ),
        ),
        Trace(
            index=2,
            header=TraceHeader(
                energy_source_point=101,
                source_x=1200,
                source_y=2200,
                coordinate_scalar=1,
                coordinate_units=1,
            ),
        ),
    ]

    result = analyzer.analyze(traces)

    assert result.total_trace_count == 3
    assert result.unique_shot_point_count == 2
    assert result.missing_shot_point_count == 0

    assert result.shot_points[0].number == 100
    assert len(
        result.shot_points[0].coordinates
    ) == 2

    assert result.shot_points[1].number == 101
    
def test_analyzer_applies_coordinate_scalar() -> None:

    transformer = CoordinateTransformer()

    analyzer = ShotPointAnalyzer(
        coordinate_transformer=transformer
    )

    traces = [
        Trace(
            index=0,
            header=TraceHeader(
                energy_source_point=100,
                source_x=1000,
                source_y=2000,
                coordinate_scalar=10,
                coordinate_units=1,
            ),
        )
    ]

    result = analyzer.analyze(traces)

    coordinate = (
        result.shot_points[0].coordinates[0]
    )

    assert coordinate.x == 10000
    assert coordinate.y == 20000