from pathlib import Path
from unittest.mock import Mock

from app.domain.models.binary_header import (
    BinaryHeader,
)
from app.domain.models.segy_metadata import (
    SegyMetadata,
)
from app.domain.models.textual_header import (
    TextualHeader,
)
from app.services.metadata_extractor import (
    MetadataExtractor,
)


def test_extract_metadata() -> None:

    reader = Mock()

    metadata = SegyMetadata(
        file_name="test.sgy",
        file_size_bytes=1000,
        trace_count=10,
        textual_header=TextualHeader(
            raw_text="",
            encoding="ascii",
            lines=[],
        ),
        binary_header=Mock(spec=BinaryHeader),
    )

    reader.read_metadata.return_value = (
        metadata
    )

    extractor = MetadataExtractor(reader)

    result = extractor.extract(
        Path("test.sgy")
    )

    assert result.file_name == "test.sgy"
    assert result.trace_count == 10