from app.domain.models.trace import Trace
from app.domain.models.trace_header import TraceHeader
from app.services.trace_header_profiler import (
    TraceHeaderProfiler,
)


def create_trace(
    index: int,
    sp: int,
    x: int,
    y: int,
) -> Trace:

    header = TraceHeader(
        trace_sequence_number=index + 1,
        trace_sequence_number_within_line=index + 1,
        original_field_record_number=100,
        trace_number_within_field_record=index + 1,
        energy_source_point=sp,
        cdp_ensemble_number=200,
        cdp_trace_number=index + 1,
        source_x=x,
        source_y=y,
        coordinate_scalar=1,
        coordinate_units=0,
    )

    return Trace(
        index=index,
        header=header,
        samples=None,
    )


def test_profile_trace_headers() -> None:
    traces = [
        create_trace(
            index=0,
            sp=153,
            x=1000,
            y=2000,
        ),
        create_trace(
            index=1,
            sp=154,
            x=1001,
            y=2001,
        ),
        create_trace(
            index=2,
            sp=154,
            x=1002,
            y=2002,
        ),
    ]

    profiler = TraceHeaderProfiler()

    profile = profiler.profile(traces)

    assert profile.trace_count == 3

    sp = profile.fields[
        "energy_source_point"
    ]

    assert sp.total_count == 3
    assert sp.missing_count == 0
    assert sp.unique_count == 2
    assert sp.minimum == 153
    assert sp.maximum == 154

    assert sp.values[153] == 1
    assert sp.values[154] == 2