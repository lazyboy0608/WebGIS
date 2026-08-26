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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
