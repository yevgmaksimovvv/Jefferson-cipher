from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
DEFAULT_SECRET_KEY = "change-me-in-local-dev-secret-key-32-bytes-minimum"


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из окружения или .env файла."""

    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_PATH), extra="ignore")

    PROJECT_NAME: str = "Jefferson Cipher Service"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = ""
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_REFRESH_PER_MINUTE: int = 10
    RATE_LIMIT_CIPHER_PER_MINUTE: int = 10
    RATE_LIMIT_MUTATION_PER_MINUTE: int = 10
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        secret_key = self.SECRET_KEY
        if not secret_key:
            raise ValueError("SECRET_KEY must not be empty")
        if len(secret_key.encode("utf-8")) < 32:
            raise ValueError("SECRET_KEY must be at least 32 bytes long")
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        if self.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")
        if self.RATE_LIMIT_AUTH_PER_MINUTE <= 0:
            raise ValueError("RATE_LIMIT_AUTH_PER_MINUTE must be greater than 0")
        if self.RATE_LIMIT_REFRESH_PER_MINUTE <= 0:
            raise ValueError("RATE_LIMIT_REFRESH_PER_MINUTE must be greater than 0")
        if self.RATE_LIMIT_CIPHER_PER_MINUTE <= 0:
            raise ValueError("RATE_LIMIT_CIPHER_PER_MINUTE must be greater than 0")
        if self.RATE_LIMIT_MUTATION_PER_MINUTE <= 0:
            raise ValueError("RATE_LIMIT_MUTATION_PER_MINUTE must be greater than 0")

        return self


@lru_cache
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек приложения."""
    return Settings()
