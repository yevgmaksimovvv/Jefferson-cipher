from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_PATH), extra="ignore")

    PROJECT_NAME: str = "Jefferson Cipher Service"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "local"
    SECRET_KEY: str = "change-me-in-local-dev-secret-key-32-bytes-minimum"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = ""
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
