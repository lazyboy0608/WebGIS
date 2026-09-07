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
        # If filename is an absolute path to a file that exists on local disk, return it directly
        try:
            path_obj = Path(filename)
            if path_obj.exists() and path_obj.is_file():
                return path_obj
        except Exception:
            pass

        raw_name = str(filename).replace("\\", "/")
        if raw_name.startswith("/"):
            raw_name = raw_name[1:]

        # Strip Windows drive letters (e.g. "D:/path/to/file.sgy" -> "file.sgy")
        if ":" in raw_name:
            clean_key = Path(raw_name).name
        else:
            clean_key = raw_name

        object_name = clean_key if clean_key.startswith("uploads/") else f"uploads/{clean_key}"
        cached_filename = object_name.replace("/", "_")
        local_path = self.temp_dir / cached_filename

        # Check if already cached in temp directory
        if not local_path.exists():
            direct_cached = self.temp_dir / clean_key.replace("/", "_")
            if direct_cached.exists():
                return direct_cached

        if not local_path.exists():
            # Try object_name ("uploads/...") first
            try:
                self.client.fget_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    file_path=str(local_path),
                )
            except Exception:
                # Try clean_key directly if uploads/ failed
                try:
                    self.client.fget_object(
                        bucket_name=self.bucket_name,
                        object_name=clean_key,
                        file_path=str(local_path),
                    )
                except Exception as exc:
                    raise FileNotFoundError(
                        f"Object '{clean_key}' not found in MinIO bucket '{self.bucket_name}': {exc}"
                    ) from exc

        return local_path

    def delete(
        self,
        path: Path | str,
    ) -> None:
        """
        Delete an object from MinIO bucket and remove any local cached copy.
        """
        path_str = str(path).replace("\\", "/")
        if ":" in path_str:
            clean_key = Path(path_str).name
        else:
            clean_key = path_str.lstrip("/")

        # If local file exists, remove local file
        try:
            if Path(path).exists():
                Path(path).unlink(missing_ok=True)
        except Exception:
            pass

        # Remove from MinIO using clean key
        for candidate_key in [
            clean_key if clean_key.startswith("uploads/") else f"uploads/{clean_key}",
            clean_key,
        ]:
            try:
                self.client.remove_object(
                    bucket_name=self.bucket_name,
                    object_name=candidate_key,
                )
            except Exception:
                pass

        # Also cleanup cached file
        cached_path = self.temp_dir / clean_key.replace("/", "_")
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
        raw_name = str(object_name).replace("\\", "/")
        if ":" in raw_name:
            clean_key = Path(raw_name).name
        else:
            clean_key = raw_name.lstrip("/")

        clean_object_name = (
            clean_key if clean_key.startswith("uploads/") else f"uploads/{clean_key}"
        )
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=clean_object_name,
            expires=timedelta(seconds=expires_seconds),
        )
