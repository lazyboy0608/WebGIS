import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Storage settings
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    LOCAL_STORAGE_DIR: Path = Path(os.getenv("LOCAL_STORAGE_DIR", "storage/segy"))

    # MinIO / S3 configurations
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    MINIO_BUCKET_RAW: str = os.getenv("MINIO_BUCKET_RAW", "raw-segy")
    MINIO_BUCKET_PROCESSED: str = os.getenv(
        "MINIO_BUCKET_PROCESSED", "processed-segy"
    )
    MINIO_BUCKET_BLOCKS_RAW: str = os.getenv("MINIO_BUCKET_BLOCKS_RAW", "blocks-raw-inputs")


settings = Settings()
