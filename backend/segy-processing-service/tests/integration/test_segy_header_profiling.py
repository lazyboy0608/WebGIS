from pathlib import Path

from app.infrastructure.segy.segyio_reader import (
    SegyIOReader,
)
from app.services.segy_reader import (
    SegyReaderService,
)
from app.services.segy_validator import (
    SegyValidator,
)
from app.services.trace_header_profiler import (
    TraceHeaderProfiler,
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


def test_profile_slb1_trace_headers() -> None:
    reader_service = create_reader_service()

    traces = reader_service.iter_traces(
        file_path=SEGY_FILE,
        include_samples=False,
    )

    profiler = TraceHeaderProfiler()

    profile = profiler.profile(traces)

    assert profile.trace_count == 630

    sp = profile.fields[
        "energy_source_point"
    ]

    assert sp.total_count == 630
    assert sp.missing_count == 0
    assert sp.unique_count == 316
    assert sp.minimum == 153
    assert sp.maximum == 468

    x = profile.fields["source_x"]

    assert x.total_count == 630
    assert x.missing_count == 0
    assert x.minimum == 1610133
    assert x.maximum == 1610154

    y = profile.fields["source_y"]

    assert y.total_count == 630
    assert y.missing_count == 0
    assert y.minimum == -191584
    assert y.maximum == -156966

    scalar = profile.fields[
        "coordinate_scalar"
    ]

    assert scalar.unique_count == 1
    assert scalar.values[1] == 630

    units = profile.fields[
        "coordinate_units"
    ]

    assert units.unique_count == 1
    assert units.values[0] == 630