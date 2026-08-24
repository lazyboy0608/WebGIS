from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "data-serving"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:06082004@localhost:5432/webgis"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
