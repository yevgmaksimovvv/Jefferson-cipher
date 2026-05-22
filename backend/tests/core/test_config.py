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


def test_settings_reads_secret_key_from_env(monkeypatch, isolated_settings) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 32)

    settings = config_module.get_settings()

    assert settings.SECRET_KEY == "x" * 32


def test_settings_reads_access_token_expire_minutes_from_env(
    monkeypatch, isolated_settings
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    settings = config_module.get_settings()

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 45


def test_default_secret_key_has_minimum_length(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert len(settings.SECRET_KEY.encode("utf-8")) >= 32


def test_default_access_token_expire_minutes_is_30(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30


def test_default_algorithm_is_hs256(isolated_settings) -> None:
    settings = config_module.get_settings()

    assert settings.ALGORITHM == "HS256"
