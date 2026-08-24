from dataclasses import dataclass

from app.domain.enums.data_format import SeismicDataFormat


@dataclass(slots=True)
class BinaryHeader:
    sample_interval_microseconds: int
    samples_per_trace: int
    sample_format: SeismicDataFormat

    ensemble_fold: int
    measurement_system: int

    segy_revision_major: int | None = None
    segy_revision_minor: int | None = None