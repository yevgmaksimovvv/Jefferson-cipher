from __future__ import annotations

import contextlib
import importlib
import importlib.util
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.core.config import ROOT_ENV_PATH, Settings
from app.db import init_db
from app.db import session as db_session

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_alembic_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    module_name: str = "alembic_env_test",
) -> tuple[object, dict[str, object]]:
    context_module = importlib.import_module("alembic.context")
    captured: dict[str, object] = {}

    class FakeConfig:
        config_file_name = None
        config_ini_section = "alembic"

        def get_section(self, section: str, default=None):
            return {}

        def get_main_option(self, key: str) -> str:
            return ""

        def set_main_option(self, key: str, value: str) -> None:
            captured[key] = value

    monkeypatch.setattr(context_module, "config", FakeConfig(), raising=False)
    monkeypatch.setattr(context_module, "is_offline_mode", lambda: True, raising=False)
    monkeypatch.setattr(
        context_module,
        "configure",
        lambda **kwargs: captured.update(kwargs),
        raising=False,
    )
    monkeypatch.setattr(
        context_module,
        "begin_transaction",
        lambda: contextlib.nullcontext(),
        raising=False,
    )
    monkeypatch.setattr(context_module, "run_migrations", lambda: None, raising=False)

    spec = importlib.util.spec_from_file_location(
        module_name, REPO_ROOT / "backend/alembic/env.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch.object(Path, "exists", lambda self: False):
        spec.loader.exec_module(module)
    return module, captured


def test_alembic_database_url_priority(monkeypatch):
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    monkeypatch.setenv("ALEMBIC_DATABASE_URL", "sqlite:///alembic.db")
    monkeypatch.setenv("DATABASE_URL_LOCAL", "sqlite:///local.db")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///container.db")

    _, captured = _load_alembic_env(monkeypatch)

    assert captured["sqlalchemy.url"] == "sqlite:///alembic.db"
    assert captured["url"] == "sqlite:///alembic.db"


def test_alembic_database_url_local_is_ignored(monkeypatch):
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    monkeypatch.setenv("DATABASE_URL_LOCAL", "sqlite:///local.db")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///container.db")

    _, captured = _load_alembic_env(monkeypatch)

    assert captured["sqlalchemy.url"] == "sqlite:///container.db"


def test_alembic_database_url_falls_back_to_database_url(monkeypatch):
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    monkeypatch.setenv("DATABASE_URL", "sqlite:///container.db")

    _, captured = _load_alembic_env(monkeypatch)

    assert captured["sqlalchemy.url"] == "sqlite:///container.db"


def test_alembic_database_url_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="Alembic database URL is not configured"):
        _load_alembic_env(monkeypatch)


def test_load_root_env_handles_comments_blank_lines_and_export_prefix(
    monkeypatch, tmp_path
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        textwrap.dedent(
            """
            # comment line

            export DATABASE_URL=sqlite:///root.db
            DATABASE_URL_LOCAL="sqlite:///local.db"
            malformed-line
            export ALEMBIC_DATABASE_URL=sqlite:///alembic.db
            # another comment
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_LOCAL", raising=False)
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", "sqlite:///alembic.db")

    module, _ = _load_alembic_env(monkeypatch, module_name="alembic_env_env_test")
    module.load_root_env(env_path)

    assert os.environ["DATABASE_URL"] == "sqlite:///root.db"
    assert os.environ["DATABASE_URL_LOCAL"] == "sqlite:///local.db"
    assert os.environ["ALEMBIC_DATABASE_URL"] == "sqlite:///alembic.db"


def test_load_root_env_missing_file_is_noop(monkeypatch):
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", "sqlite:///alembic.db")
    module, _ = _load_alembic_env(monkeypatch, module_name="alembic_env_missing_env")

    module.load_root_env(ROOT_ENV_PATH.parent / "does-not-exist.env")


def test_settings_env_file_is_absolute_root_path():
    assert ROOT_ENV_PATH.is_absolute()
    assert Settings.model_config["env_file"] == str(ROOT_ENV_PATH)


def test_get_engine_raises_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        db_session,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL=""),
    )

    with pytest.raises(RuntimeError, match="Database URL is not configured"):
        db_session.get_engine()


def test_session_module_import_does_not_create_engine(monkeypatch):
    module = importlib.import_module("app.db.session")
    with patch(
        "sqlalchemy.create_engine",
        side_effect=AssertionError("create_engine should not be called during import"),
    ):
        importlib.reload(module)
    importlib.reload(module)


def test_get_engine_uses_explicit_url_without_stale_cache():
    module = importlib.import_module("app.db.session")
    engine_one = module.get_engine("sqlite:///one.db")
    engine_two = module.get_engine("sqlite:///two.db")

    assert str(engine_one.url) == "sqlite:///one.db"
    assert str(engine_two.url) == "sqlite:///two.db"
    assert engine_one is not engine_two


def test_get_db_closes_session_after_finalization(monkeypatch):
    module = importlib.import_module("app.db.session")

    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()
    monkeypatch.setattr(module, "get_session_factory", lambda: lambda: fake_session)

    generator = module.get_db()
    yielded_session = next(generator)

    assert yielded_session is fake_session
    assert not fake_session.closed

    generator.close()

    assert fake_session.closed


def test_init_db_main_returns_zero_with_in_memory_session(
    in_memory_engine, monkeypatch
):
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=in_memory_engine, expire_on_commit=False)
    monkeypatch.setattr(init_db, "get_session_factory", lambda: SessionLocal)

    assert init_db.main() == 0
