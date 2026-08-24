from dataclasses import dataclass


@dataclass(slots=True)
class TraceHeader:
    trace_sequence_number: int | None = None
    trace_sequence_number_within_line: int | None = None

    original_field_record_number: int | None = None
    trace_number_within_field_record: int | None = None

    energy_source_point: int | None = None

    cdp_ensemble_number: int | None = None
    cdp_trace_number: int | None = None

    source_x: float | None = None
    source_y: float | None = None

    coordinate_scalar: int | None = None
    coordinate_units: int | None = None