from collections.abc import Iterator
from pathlib import Path

from app.domain.interfaces.segy_reader import SegyReader
from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.trace import Trace
from app.services.segy_validator import SegyValidator


class SegyReaderService:
    """
    Application service responsible for reading SEG-Y files.

    This service coordinates validation and the actual
    SEG-Y reader implementation.
    """

    def __init__(
        self,
        reader: SegyReader,
        validator: SegyValidator,
    ) -> None:
        self._reader = reader
        self._validator = validator

    def read_metadata(
        self,
        file_path: Path,
    ) -> SegyMetadata:
        """
        Validate the SEG-Y file and read its metadata.
        """

        self._validator.validate(file_path)

        return self._reader.read_metadata(
            file_path
        )

    def iter_traces(
        self,
        file_path: Path,
        include_samples: bool = False,
    ) -> Iterator[Trace]:
        """
        Validate the SEG-Y file and lazily iterate
        through its traces.
        """

        self._validator.validate(file_path)

        yield from self._reader.iter_traces(
            file_path=file_path,
            include_samples=include_samples,
        )