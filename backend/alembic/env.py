from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from sqlalchemy import engine_from_config, pool

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_PATH = REPO_ROOT / ".env"


def load_root_env(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_database_url() -> str:
    # 1. Явный override для one-shot команд
    # 2. Основной URL базы данных
    for name in ("ALEMBIC_DATABASE_URL", "DATABASE_URL"):
        value = os.getenv(name, "")
        if value:
            return value
    raise RuntimeError(
        "Alembic database URL is not configured. Set ALEMBIC_DATABASE_URL or "
        "DATABASE_URL in the environment."
    )


load_root_env(ROOT_ENV_PATH)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_database_url()
    config.set_main_option("sqlalchemy.url", url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_database_url()
    config.set_main_option("sqlalchemy.url", url)
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
