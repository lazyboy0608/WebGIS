from dataclasses import dataclass

from app.domain.models.binary_header import BinaryHeader
from app.domain.models.textual_header import TextualHeader


@dataclass(slots=True)
class SegyMetadata:
    file_name: str
    file_size_bytes: int

    trace_count: int

    textual_header: TextualHeader
    binary_header: BinaryHeader