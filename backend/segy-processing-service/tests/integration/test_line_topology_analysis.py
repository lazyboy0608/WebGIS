from pathlib import Path

from app.infrastructure.segy.segyio_reader import SegyIOReader
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.segy_validator import SegyValidator
from app.services.trace_processor import TraceProcessor


def test_analyze_slb1_line_topology() -> None:
    file_path = Path(
        "data/input/slb1.sgy"
    )

    validator = SegyValidator()

    reader = SegyIOReader()

    transformer = CoordinateTransformer()

    trace_processor = TraceProcessor(
        transformer
    )

    topology_analyzer = LineTopologyAnalyzer(
        gap_threshold=100
    )

    validator.validate(file_path)

    traces = reader.iter_traces(
        file_path=file_path,
        include_samples=False,
    )

    processed_traces = (
        trace_processor.process(trace)
        for trace in traces
    )

    result = topology_analyzer.analyze(
        processed_traces
    )

    assert result.trace_count == 630

    assert result.coordinate_count == 630

    assert result.distance_count == 629

    assert result.minimum_distance is not None
    assert result.maximum_distance is not None
    assert result.average_distance is not None
    assert result.median_distance is not None

    assert result.start_coordinate is not None
    assert result.end_coordinate is not None

    assert result.gap_count == 0
    assert result.maximum_gap is None

    assert result.reversed_segment_count >= 0

    assert isinstance(
        result.monotonic_shot_point,
        bool,
    )

    assert isinstance(
        result.continuous,
        bool,
    )