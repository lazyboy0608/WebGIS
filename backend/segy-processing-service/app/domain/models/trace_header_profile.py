from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldStatistics:
    """
    Statistics for a single SEG-Y trace header field.
    """

    field_name: str

    total_count: int = 0

    missing_count: int = 0

    unique_count: int = 0

    minimum: int | float | None = None

    maximum: int | float | None = None

    values: dict[Any, int] = field(
        default_factory=dict
    )


@dataclass
class TraceHeaderProfile:
    """
    Profiling result for SEG-Y trace headers.
    """

    trace_count: int

    fields: dict[str, FieldStatistics] = field(
        default_factory=dict
    )