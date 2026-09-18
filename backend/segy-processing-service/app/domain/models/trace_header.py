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

    group_x: float | None = None
    group_y: float | None = None

    cdp_x: float | None = None
    cdp_y: float | None = None

    elevation_scalar: int | None = None
    coordinate_scalar: int | None = None
    coordinate_units: int | None = None

    @property
    def effective_coordinate_scalar(self) -> int:
        """
        Xác định hệ số tỷ lệ tọa độ hiệu dụng (SAC/SAED fallback).
        - Ưu tiên SourceGroupScalar (SAC - bytes 71-72) nếu khác 0 và khác 1.
        - Fallback sang ElevationScalar (SAED - bytes 69-70) nếu SAC không hợp lệ nhưng SAED khác 0 và khác 1.
        - Mặc định là 1 nếu cả hai đều không hợp lệ.
        """
        if self.coordinate_scalar is not None and self.coordinate_scalar not in (0, 1):
            return self.coordinate_scalar
        if self.elevation_scalar is not None and self.elevation_scalar not in (0, 1):
            return self.elevation_scalar
        return 1