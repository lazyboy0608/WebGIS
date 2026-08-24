from pathlib import Path

from app.infrastructure.segy.segyio_reader import (
    SegyIOReader,
)
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)
from app.services.segy_reader import (
    SegyReaderService,
)
from app.services.segy_validator import (
    SegyValidator,
)
from app.services.trace_processor import (
    TraceProcessor,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SEGY_FILE = (
    PROJECT_ROOT
    / "data"
    / "input"
    / "slb1.sgy"
)


def create_reader_service() -> SegyReaderService:
    return SegyReaderService(
        reader=SegyIOReader(),
        validator=SegyValidator(),
    )


def create_trace_processor() -> TraceProcessor:
    return TraceProcessor(
        coordinate_transformer=CoordinateTransformer(),
    )


def test_process_slb1_segy() -> None:
    reader_service = create_reader_service()
    processor = create_trace_processor()

    traces = reader_service.iter_traces(
        file_path=SEGY_FILE,
        include_samples=False,
    )

    processed_traces = list(
        processor.process_many(traces)
    )

    # --------------------------------------------------
    # Trace count
    # --------------------------------------------------

    assert len(processed_traces) == 630

    # --------------------------------------------------
    # First trace
    # --------------------------------------------------

    first = processed_traces[0]

    assert first.trace_index == 0
    assert first.source_point.number == 153

    assert first.coordinate.x == 1610154
    assert first.coordinate.y == -191584

    # Samples must not be loaded
    assert first.samples is None

    # --------------------------------------------------
    # Last trace
    # --------------------------------------------------

    last = processed_traces[-1]

    assert last.trace_index == 629

    # --------------------------------------------------
    # All traces must have valid coordinates
    # --------------------------------------------------

    for trace in processed_traces:
        assert trace.coordinate.x is not None
        assert trace.coordinate.y is not None