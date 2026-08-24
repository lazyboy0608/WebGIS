from pathlib import Path
from uuid import uuid4

from app.domain.services.file_storage import FileStorage


class LocalFileStorage(FileStorage):
    """Store files on the local filesystem."""

    def __init__(self, base_directory: str | Path):
        self.base_directory = Path(base_directory).resolve()

        self.base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        filename: str,
        content: bytes,
    ) -> Path:
        requested_path = (
            self.base_directory / filename
        ).resolve()

        if self.base_directory not in requested_path.parents:
            raise ValueError(
                "Filename resolves outside storage directory."
            )


        file_path = requested_path
        if file_path.exists():
            file_path = file_path.with_name(
                f"{file_path.stem}-{uuid4().hex}{file_path.suffix}"
            )

        file_path.write_bytes(content)

        return file_path

    def get_path(
        self,
        filename: str,
    ) -> Path:
        file_path = (
            self.base_directory / filename
        ).resolve()

        self._validate_path(file_path)

        return file_path

    def delete(
        self,
        path: Path,
    ) -> None:
        if path.exists():
            path.unlink()

    def _validate_path(
        self,
        file_path: Path,
    ) -> None:
        if (
            self.base_directory != file_path
            and self.base_directory
            not in file_path.parents
        ):
            raise ValueError(
                "Filename resolves outside storage directory."
            )
