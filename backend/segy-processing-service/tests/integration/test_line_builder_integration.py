from pathlib import Path

from app.infrastructure.segy.segyio_reader import SegyIOReader
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.line_builder import LineBuilder
from app.services.segy_validator import SegyValidator
from app.services.trace_processor import TraceProcessor


def test_build_slb1_line() -> None:
    file_path = Path(
        "data/input/slb1.sgy"
    )

    validator = SegyValidator()

    reader = SegyIOReader()

    transformer = CoordinateTransformer()

    trace_processor = TraceProcessor(
        transformer
    )

    line_builder = LineBuilder()

    validator.validate(file_path)

    traces = reader.iter_traces(
        file_path=file_path,
        include_samples=False,
    )

    processed_traces = (
        trace_processor.process(trace)
        for trace in traces
    )

    line = line_builder.build(
        processed_traces
    )

    assert line is not None

    assert len(line.coordinates) == 630

    assert len(line.trace_indices) == 630

    assert len(line.shot_points) == 630

    assert line.trace_indices[0] == 0

    assert line.trace_indices[-1] == 629

    assert line.coordinates[0].x == 1610154

    assert line.coordinates[0].y == -191584

    assert line.coordinates[-1].x == 1610134

    assert line.coordinates[-1].y == -156966

    assert line.shot_points[0] == 153

    assert line.shot_points[-1] == 468