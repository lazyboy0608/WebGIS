from pathlib import Path

from pyproj import transformer

from app.infrastructure.segy.segyio_reader import (
    SegyIOReader,
)
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.segy_reader import (
    SegyReaderService,
)
from app.services.segy_validator import (
    SegyValidator,
)
from app.services.shot_point_analyzer import (
    ShotPointAnalyzer,
)


def test_analyze_slb1_shot_points() -> None:

    file_path = Path(
        "data/input/slb1.sgy"
    )

    reader = SegyIOReader()

    validator = SegyValidator()

    service = SegyReaderService(
        reader=reader,
        validator=validator,
    )

    transformer = CoordinateTransformer()

    analyzer = ShotPointAnalyzer(
        coordinate_transformer=transformer
    )

    traces = service.iter_traces(
        file_path=file_path,
        include_samples=False,
    )

    result = analyzer.analyze(traces)

    assert result.total_trace_count == 630

    assert result.unique_shot_point_count == 316

    assert result.missing_shot_point_count == 0

    assert result.min_shot_point == 153

    assert result.max_shot_point == 468