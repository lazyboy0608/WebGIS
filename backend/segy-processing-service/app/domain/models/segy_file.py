from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SegyFile:
    filename: str
    file_path: str
    file_size: int
    source_crs: str
    trace_count: int
    line_count: int
    geometry: Any = None

    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None