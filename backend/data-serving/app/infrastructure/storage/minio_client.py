import io
from datetime import timedelta
from minio import Minio

from app.config import settings


class MinioClientManager:
    """Manages MinIO client connections and operations in data-serving."""

    def __init__(
        self,
        endpoint: str = settings.minio_endpoint,
        access_key: str = settings.minio_access_key,
        secret_key: str = settings.minio_secret_key,
        secure: bool = settings.minio_secure,
        client: Minio | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = client or Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self, bucket_name: str) -> None:
        """Create bucket if missing."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except Exception:
            pass

    def _clean_key(self, object_name: str) -> str:
        from pathlib import Path
        path_str = str(object_name).replace("\\", "/")
        if ":" in path_str:
            return Path(path_str).name
        return path_str.lstrip("/")

    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload byte data to MinIO and return object name."""
        self.ensure_bucket(bucket_name)
        clean_object_name = self._clean_key(object_name)
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=bucket_name,
            object_name=clean_object_name,
            data=stream,
            length=len(data),
            content_type=content_type,
        )
        return clean_object_name

    def get_presigned_download_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_seconds: int = settings.minio_presigned_expiry_seconds,
        filename: str | None = None,
    ) -> str:
        """
        Generate a presigned GET URL for downloading an object.
        Optionally set response headers to force download filename.
        """
        clean_object_name = self._clean_key(object_name)
        response_headers = None
        if filename:
            response_headers = {
                "response-content-disposition": f'attachment; filename="{filename}"'
            }

        return self.client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=clean_object_name,
            expires=timedelta(seconds=expires_seconds),
            response_headers=response_headers,
        )


minio_manager = MinioClientManager()
