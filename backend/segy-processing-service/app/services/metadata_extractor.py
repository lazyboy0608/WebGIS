from pathlib import Path

from app.domain.interfaces.segy_reader import SegyReader
from app.domain.models.segy_metadata import SegyMetadata


class MetadataExtractor:

    def __init__(
        self,
        segy_reader: SegyReader,
    ) -> None:
        self._segy_reader = segy_reader

    def extract(
        self,
        file_path: Path,
    ) -> SegyMetadata:

        return self._segy_reader.read_metadata(
            file_path
        )