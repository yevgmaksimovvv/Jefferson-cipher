from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

import app.core.config as config_module
import app.core.rate_limit as rate_limit_module
import pytest

health_module = import_module("app.api.v1.endpoints.health")


@dataclass
class FakeResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(
        self,
        *,
        fail_connect: bool = False,
        fail_migrations: bool = False,
        revision: str = "0004",
        disks_count: int = 36,
        missing_seed: bool = False,
    ):
        self.fail_connect = fail_connect
        self.fail_migrations = fail_migrations
        self.revision = revision
        self.disks_count = disks_count
        self.missing_seed = missing_seed
        self.closed = False

    def execute(self, statement):
        query = str(statement)
        if self.fail_connect:
            raise health_module.SQLAlchemyError("db unavailable")
        if "SELECT 1" in query:
            return FakeResult(1)
        if "FROM alembic_version" in query:
            if self.fail_migrations:
                raise health_module.SQLAlchemyError("table missing")
            return FakeResult(self.revision)
        raise AssertionError(f"Unexpected statement: {query}")

    def scalar(self, statement):
        query = str(statement)
        if "FROM disk_sets" in query:
            return None if self.missing_seed else 1
        if "FROM disks" in query:
            return self.disks_count
        raise AssertionError(f"Unexpected statement: {query}")

    def close(self):
        self.closed = True


class FakeRedisClient:
    def __init__(self, *, fail_ping: bool = False):
        self.fail_ping = fail_ping

    def ping(self):
        if self.fail_ping:
            raise rate_limit_module.RateLimiterUnavailable()
        return True


def test_ready_endpoint_returns_200_when_database_migrated_and_seeded(
    client, monkeypatch
):
    fake_session = FakeSession()
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(health_module, "_get_alembic_head_revision", lambda: "0004")

    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "migrations": "ok",
        "seed": "ok",
        "rate_limiter": "memory",
    }
    assert fake_session.closed is True


def test_ready_endpoint_returns_503_when_db_connection_fails(client, monkeypatch):
    fake_session = FakeSession(fail_connect=True)
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "error",
        "migrations": "unknown",
        "seed": "unknown",
        "rate_limiter": "unknown",
    }
    assert fake_session.closed is True


def test_ready_endpoint_returns_not_ready_when_migrations_do_not_match_head(
    client, monkeypatch
):
    fake_session = FakeSession(revision="0003")
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(health_module, "_get_alembic_head_revision", lambda: "0004")

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "ok",
        "migrations": "error",
        "seed": "unknown",
        "rate_limiter": "unknown",
    }
    assert fake_session.closed is True


def test_ready_endpoint_returns_not_ready_when_migrations_query_fails(
    client, monkeypatch
):
    fake_session = FakeSession(fail_migrations=True)
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "ok",
        "migrations": "error",
        "seed": "unknown",
        "rate_limiter": "unknown",
    }
    assert fake_session.closed is True


@pytest.mark.parametrize("disks_count, missing_seed", [(35, False), (36, True)])
def test_ready_endpoint_returns_not_ready_when_seed_is_missing_or_corrupted(
    client,
    monkeypatch,
    disks_count,
    missing_seed,
):
    fake_session = FakeSession(disks_count=disks_count, missing_seed=missing_seed)
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(health_module, "_get_alembic_head_revision", lambda: "0004")

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "ok",
        "migrations": "ok",
        "seed": "error",
        "rate_limiter": "unknown",
    }
    assert fake_session.closed is True


def test_ready_endpoint_reports_redis_rate_limiter_ok(client, monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(health_module, "_get_alembic_head_revision", lambda: "0004")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    config_module.get_settings.cache_clear()
    monkeypatch.setattr(
        rate_limit_module,
        "_create_redis_client",
        lambda redis_url: FakeRedisClient(),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "migrations": "ok",
        "seed": "ok",
        "rate_limiter": "ok",
    }
    assert fake_session.closed is True


def test_ready_endpoint_reports_redis_rate_limiter_error(client, monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(
        health_module, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(health_module, "_get_alembic_head_revision", lambda: "0004")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    config_module.get_settings.cache_clear()
    monkeypatch.setattr(
        rate_limit_module,
        "_create_redis_client",
        lambda redis_url: FakeRedisClient(fail_ping=True),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "ok",
        "migrations": "ok",
        "seed": "ok",
        "rate_limiter": "error",
    }
    assert fake_session.closed is True
