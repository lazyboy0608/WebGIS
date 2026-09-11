from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "data-serving"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:06082004@localhost:5432/webgis"

    # Access token — ngắn hạn (15 phút)
    jwt_secret_key: str = "webgis_super_secret_jwt_key_2026_seismic_data_serving"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    # Refresh token — dài hạn (7 ngày), dùng secret key riêng
    refresh_secret_key: str = "webgis_refresh_secret_key_2026_do_not_share"
    refresh_token_expire_days: int = 7

    # Rate limiting — sliding window (in-memory, Phase 1)
    # Override via environment variables, e.g. RATE_LIMIT_LOGIN=5
    rate_limit_window_seconds: int = 60   # Window size for all rate limits
    rate_limit_login: int = 10            # POST /api/v1/auth/login (per IP)
    rate_limit_register: int = 5          # POST /api/v1/auth/register (per IP)
    rate_limit_refresh: int = 10          # POST /api/v1/auth/refresh (per IP)
    rate_limit_clip: int = 15             # POST /api/segy-files/{id}/processed/lines/clip (per user)

    # MinIO / S3 Object Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_raw: str = "raw-segy"
    minio_bucket_processed: str = "processed-segy"
    minio_bucket_avatars: str = "user-avatars"
    minio_presigned_expiry_seconds: int = 3600

    # Redis Cache (db 0 for Data Serving)
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_enabled: bool = True
    redis_mvt_ttl_seconds: int = 86400       # 24 hours for MVT vector tiles
    redis_blocks_ttl_seconds: int = 86400    # 24 hours for Seismic blocks GeoJSON
    redis_segy_ttl_seconds: int = 86400      # 24 hours for SEG-Y survey metadata/lines

    # Default Admin Seed on Startup
    default_admin_email: str = "admin@webgis.com"
    default_admin_password: str = "Admin@123456"
    default_admin_fullname: str = "System Administrator"
    default_admin_phone: str = "0987654321"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
