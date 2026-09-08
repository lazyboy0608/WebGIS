import pytest

from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.textual_header import TextualHeader
from app.services.source_crs_extractor import extract_source_crs


def make_metadata(text: str) -> SegyMetadata:
    return SegyMetadata(
        file_name="survey.sgy",
        file_size_bytes=1,
        trace_count=1,
        textual_header=TextualHeader(
            raw_text=text,
            encoding="ascii",
            lines=[text],
        ),
        binary_header=None,
    )


def test_extract_source_crs_from_textual_header() -> None:
    metadata = make_metadata("C07 Projection: [EPSG:32605] WGS 84 / UTM zone 5N")

    assert extract_source_crs(metadata) == "EPSG:32605"


def test_extract_source_crs_accepts_case_insensitive_epsg() -> None:
    metadata = make_metadata("Projection: [epsg=26782]")

    assert extract_source_crs(metadata) == "EPSG:26782"


def test_extract_source_crs_from_utm_textual_header() -> None:
    metadata = make_metadata("PROJECTION: UTM49N DATUM: WGS84")

    assert extract_source_crs(metadata) == "EPSG:32649"


def test_extract_source_crs_falls_back_to_default_when_no_epsg() -> None:
    metadata = make_metadata("Projection: Unknown Local Grid")

    assert extract_source_crs(metadata) == "EPSG:32649"


def test_extract_source_crs_requires_epsg_code_when_default_disabled() -> None:
    metadata = make_metadata("Projection: Unknown Local Grid")

    with pytest.raises(ValueError, match="No EPSG code found"):
        extract_source_crs(metadata, default_crs=None)