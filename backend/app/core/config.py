import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
DEFAULT_SECRET_KEY = "change-me-in-local-dev-secret-key-32-bytes-minimum"
DEFAULT_BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://localhost",
    "https://localhost:8443",
]


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
    REDIS_URL: str | None = None
    RATE_LIMIT_STORAGE: str = "auto"
    RATE_LIMIT_FAIL_OPEN: bool = False
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_REFRESH_PER_MINUTE: int = 10
    RATE_LIMIT_CIPHER_PER_MINUTE: int = 10
    RATE_LIMIT_MUTATION_PER_MINUTE: int = 10
    TRUST_PROXY_HEADERS: bool = False
    TRUSTED_PROXY_IPS: str = ""
    ENABLE_HSTS: bool = False
    HSTS_MAX_AGE_SECONDS: int = 31536000
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_BACKEND_CORS_ORIGINS)
    )

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def normalize_redis_url(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("RATE_LIMIT_STORAGE", mode="before")
    @classmethod
    def normalize_rate_limit_storage(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def normalize_backend_cors_origins(cls, value: Any) -> list[str]:
        if value in (None, ""):
            return list(DEFAULT_BACKEND_CORS_ORIGINS)
        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return list(DEFAULT_BACKEND_CORS_ORIGINS)
            if raw_value.startswith("["):
                parsed_value = json.loads(raw_value)
                if not isinstance(parsed_value, list):
                    raise ValueError("BACKEND_CORS_ORIGINS must be a list")
                value = parsed_value
            else:
                return [
                    origin.strip() for origin in raw_value.split(",") if origin.strip()
                ]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return value

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
        if self.RATE_LIMIT_STORAGE not in {"auto", "memory", "redis"}:
            raise ValueError("RATE_LIMIT_STORAGE must be one of: auto, memory, redis")
        if self.HSTS_MAX_AGE_SECONDS <= 0:
            raise ValueError("HSTS_MAX_AGE_SECONDS must be greater than 0")

        return self


@lru_cache
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек приложения."""
    return Settings()
