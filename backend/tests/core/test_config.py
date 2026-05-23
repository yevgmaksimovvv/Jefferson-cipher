from __future__ import annotations

import pytest
from app.core import config as config_module
from app.core import rate_limit as rate_limit_module


@pytest.fixture()
def isolated_settings(monkeypatch, tmp_path):
    for key in config_module.Settings.model_fields:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(
        config_module.Settings,
        "model_config",
        {
            **config_module.Settings.model_config,
            "env_file": str(tmp_path / ".env.not-used"),
        },
        raising=False,
    )
    config_module.get_settings.cache_clear()
    try:
        yield
    finally:
        config_module.get_settings.cache_clear()


def test_default_secret_key_has_minimum_length(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert len(settings.SECRET_KEY.encode("utf-8")) >= 32


def test_settings_reads_secret_key_from_env(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 32)

    settings = config_module.get_settings()

    assert settings.SECRET_KEY == "x" * 32


def test_short_secret_key_is_rejected(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 31)

    with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 bytes long"):
        config_module.get_settings()


def test_empty_secret_key_is_rejected(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("SECRET_KEY", "")

    with pytest.raises(ValueError, match="SECRET_KEY must not be empty"):
        config_module.get_settings()


def test_default_access_token_expire_minutes_is_30(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30


def test_settings_reads_access_token_expire_minutes_from_env(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    settings = config_module.get_settings()

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 45


def test_access_token_expire_minutes_must_be_positive(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")

    with pytest.raises(
        ValueError, match="ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0"
    ):
        config_module.get_settings()


def test_default_refresh_token_expire_days_is_30(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 30


def test_settings_reads_refresh_token_expire_days_from_env(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")

    settings = config_module.get_settings()

    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 14


def test_refresh_token_expire_days_must_be_positive(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "0")

    with pytest.raises(
        ValueError, match="REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0"
    ):
        config_module.get_settings()


def test_default_algorithm_is_hs256(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert settings.ALGORITHM == "HS256"


def test_default_proxy_and_cors_settings_include_local_https(
    isolated_settings,
) -> None:
    settings = config_module.get_settings()

    assert settings.TRUST_PROXY_HEADERS is False
    assert settings.TRUSTED_PROXY_IPS == ""
    assert "https://localhost:8443" in settings.BACKEND_CORS_ORIGINS


def test_invalid_rate_limit_storage_is_rejected(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "invalid")

    with pytest.raises(
        ValueError, match="RATE_LIMIT_STORAGE must be one of: auto, memory, redis"
    ):
        config_module.get_settings()


def test_redis_rate_limit_storage_requires_redis_url(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "")

    with pytest.raises(ValueError, match="RATE_LIMIT_STORAGE=redis requires REDIS_URL"):
        config_module.get_settings()


def test_auto_rate_limit_storage_without_redis_url_resolves_to_memory(
    isolated_settings,
) -> None:
    settings = config_module.Settings(RATE_LIMIT_STORAGE="auto", REDIS_URL="")

    limiter = rate_limit_module.get_rate_limiter(settings)

    assert isinstance(limiter, rate_limit_module.InMemoryRateLimiter)


def test_auto_rate_limit_storage_with_redis_url_resolves_to_redis(
    isolated_settings,
) -> None:
    settings = config_module.Settings(
        RATE_LIMIT_STORAGE="auto",
        REDIS_URL="redis://redis:6379/0",
    )

    limiter = rate_limit_module.get_rate_limiter(settings)

    assert isinstance(limiter, rate_limit_module.RedisRateLimiter)


def test_fail_open_is_rejected_when_redis_rate_limiting_is_active(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "true")

    with pytest.raises(
        ValueError,
        match="RATE_LIMIT_FAIL_OPEN is not allowed when Redis rate limiting is active",
    ):
        config_module.get_settings()


def test_fail_open_is_rejected_when_auto_resolves_to_redis(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "auto")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "true")

    with pytest.raises(
        ValueError,
        match="RATE_LIMIT_FAIL_OPEN is not allowed when Redis rate limiting is active",
    ):
        config_module.get_settings()


def test_hsts_max_age_must_be_positive(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("HSTS_MAX_AGE_SECONDS", "0")

    with pytest.raises(ValueError, match="HSTS_MAX_AGE_SECONDS must be greater than 0"):
        config_module.get_settings()


def test_backend_cors_wildcard_is_rejected(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "*")
    config_module.get_settings.cache_clear()

    with pytest.raises(
        ValueError, match="BACKEND_CORS_ORIGINS must not contain wildcard \\*"
    ):
        config_module.get_settings()
