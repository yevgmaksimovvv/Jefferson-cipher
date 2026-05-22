from __future__ import annotations

import pytest
from app.core import config as config_module


@pytest.fixture()
def isolated_settings(monkeypatch, tmp_path):
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
