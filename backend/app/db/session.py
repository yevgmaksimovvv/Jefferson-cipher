from __future__ import annotations

import os
from collections.abc import Iterator
from functools import cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_database_url(database_url: str | None = None) -> str:
    resolved = (
        database_url or get_settings().DATABASE_URL or os.getenv("DATABASE_URL", "")
    )
    if not resolved:
        raise RuntimeError(
            "Database URL is not configured. Set DATABASE_URL or pass database_url."
        )
    return resolved


@cache
def _cached_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def get_engine(database_url: str | None = None) -> Engine:
    return _cached_engine(get_database_url(database_url))


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Iterator[Session]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
