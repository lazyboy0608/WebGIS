import re

from app.domain.models.segy_metadata import SegyMetadata

EPSG_PATTERN = re.compile(r"\bEPSG\s*[:=]\s*(\d{4,6})\b", re.IGNORECASE)
DEFAULT_SOURCE_CRS = "EPSG:26782"


def extract_source_crs(
    metadata: SegyMetadata,
    default_crs: str | None = DEFAULT_SOURCE_CRS,
) -> str:
    """Extract the source CRS authority code from the SEG-Y textual header."""
    match = EPSG_PATTERN.search(metadata.textual_header.raw_text)
    if match is not None:
        return f"EPSG:{match.group(1)}"
    if default_crs is not None:
        return default_crs
    raise ValueError(
        f"No EPSG code found in SEG-Y textual header: {metadata.file_name}"
    )