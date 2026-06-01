from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    OPENROUTER_API_KEY: str = ""

    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_BUCKET_NAME: str = "garimpogov-editais"

    # B24: suporta múltiplas origens separadas por vírgula
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # B26: parâmetros do RAG
    RAG_TOP_K: int = 5
    OPENROUTER_CHAT_MODEL: str = "google/gemini-2.0-flash"

    # B34: limite de caracteres na pergunta do chat
    CHAT_MAX_QUESTION_LENGTH: int = 2000

    # B32: chave de API para autenticação nos endpoints
    API_KEY: str = ""  # vazio = sem autenticação

    @property
    def frontend_origins(self) -> list[str]:
        """Retorna lista de origens permitidas para CORS."""
        return [origin.strip() for origin in self.FRONTEND_ORIGIN.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
