from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Jefferson Cipher Service"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "local"
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
