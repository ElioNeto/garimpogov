from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/garimpogov"

    # Google Gemini
    gemini_api_key: str = ""

    # Cloudflare R2
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_endpoint_url: str = ""
    r2_bucket_name: str = "garimpogov-editais"

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # App
    app_name: str = "GarimpoGov API"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
