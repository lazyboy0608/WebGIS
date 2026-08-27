import io
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.domain.services.file_storage import FileStorage


class MinioFileStorage(FileStorage):
    """Store and retrieve files using MinIO (S3-compatible Object Storage)."""

    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        secure: bool = False,
        bucket_name: str = "raw-segy",
        client: Minio | None = None,
        temp_dir: str | Path | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.client = client or Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "webgis_segy_cache"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it does not already exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception:
            # Avoid crashing initialization if MinIO is temporarily unreachable
            pass

    def save(
        self,
        filename: str,
        content: bytes,
    ) -> Path:
        """
        Upload file content to MinIO bucket and return its stored object key path.
        """
        clean_name = Path(filename).name
        object_name = f"uploads/{uuid4().hex}_{clean_name}"

        data_stream = io.BytesIO(content)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(content),
            content_type="application/octet-stream",
        )

        # Also cache locally in temp directory so immediate processing can read it directly
        local_cache_path = self.temp_dir / object_name.replace("/", "_")
        local_cache_path.parent.mkdir(parents=True, exist_ok=True)
        local_cache_path.write_bytes(content)

        return Path(object_name)

    def get_path(
        self,
        filename: str,
    ) -> Path:
        """
        Resolve a stored object name to a local filesystem Path.
        If not cached locally, downloads the object from MinIO to temp storage.
        """
        raw_name = str(filename).replace("\\", "/")
        if raw_name.startswith("/"):
            raw_name = raw_name[1:]

        # Find object name in MinIO
        object_name = raw_name if raw_name.startswith("uploads/") else f"uploads/{raw_name}"
        cached_filename = object_name.replace("/", "_")
        local_path = self.temp_dir / cached_filename

        # Also check if raw_name exists in temp_dir directly
        if not local_path.exists():
            direct_cached = self.temp_dir / raw_name.replace("/", "_")
            if direct_cached.exists():
                return direct_cached

        if not local_path.exists():
            try:
                self.client.fget_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    file_path=str(local_path),
                )
            except Exception:
                # Try raw_name as object_name directly if uploads/ failed
                try:
                    self.client.fget_object(
                        bucket_name=self.bucket_name,
                        object_name=raw_name,
                        file_path=str(local_path),
                    )
                except Exception as exc:
                    raise FileNotFoundError(
                        f"Object '{raw_name}' not found in MinIO bucket '{self.bucket_name}': {exc}"
                    ) from exc

        return local_path


    def delete(
        self,
        path: Path | str,
    ) -> None:
        """
        Delete an object from MinIO bucket and remove any local cached copy.
        """
        object_name = str(path).replace("\\", "/")
        # If path is a local file path inside temp_dir or base_dir, extract the object name
        if self.temp_dir in Path(path).resolve().parents or Path(path).exists():
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

        # Try to delete from MinIO
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
        except Exception:
            pass

        # Also cleanup cached file if named by object_name
        cached_path = self.temp_dir / object_name.replace("/", "_")
        if cached_path.exists():
            try:
                cached_path.unlink(missing_ok=True)
            except Exception:
                pass

    def get_presigned_download_url(
        self,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate a presigned GET URL for direct download from MinIO."""
        clean_object_name = str(object_name).replace("\\", "/")
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=clean_object_name,
            expires=timedelta(seconds=expires_seconds),
        )
