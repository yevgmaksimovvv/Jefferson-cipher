import importlib

import app.db.models  # noqa: F401
import app.main as app_main_module
import pytest
from app.core import config as config_module
from app.core.rate_limit import reset_rate_limit_state
from app.db.base import Base
from app.db.session import get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _fresh_app():
    config_module.get_settings.cache_clear()
    return importlib.reload(app_main_module).app


@pytest.fixture()
def in_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db_session(in_memory_engine):
    SessionLocal = sessionmaker(bind=in_memory_engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def db_client(in_memory_engine):
    SessionLocal = sessionmaker(bind=in_memory_engine, expire_on_commit=False)
    app = _fresh_app()

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    app = _fresh_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def default_test_env(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "auto")
    monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "false")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "false")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "")
    monkeypatch.setenv("ENABLE_HSTS", "false")
    monkeypatch.setenv("HSTS_MAX_AGE_SECONDS", "31536000")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "")


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    reset_rate_limit_state()
    try:
        yield
    finally:
        reset_rate_limit_state()
