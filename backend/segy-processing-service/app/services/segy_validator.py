from pathlib import Path

from app.exceptions.segy_exceptions import (
    InvalidSegyFileException,
)


class SegyValidator:

    SUPPORTED_EXTENSIONS = {
        ".sgy",
        ".segy",
    }

    def validate(
        self,
        file_path: Path,
    ) -> None:

        if not file_path.exists():
            raise InvalidSegyFileException(
                f"SEG-Y file does not exist: {file_path}"
            )

        if not file_path.is_file():
            raise InvalidSegyFileException(
                f"Path is not a file: {file_path}"
            )

        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise InvalidSegyFileException(
                f"Unsupported SEG-Y extension: "
                f"{file_path.suffix}"
            )

        if file_path.stat().st_size == 0:
            raise InvalidSegyFileException(
                "SEG-Y file is empty"
            )