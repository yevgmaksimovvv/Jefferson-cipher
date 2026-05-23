from __future__ import annotations

import importlib
from datetime import datetime, timedelta

import app.core.rate_limit as rate_limit_module
import app.main as app_main_module
import pytest
from app.core import config as config_module
from app.core.rate_limit import (
    RateLimiterUnavailable,
    RedisRateLimiter,
    get_client_identifier,
    get_rate_limiter,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
)
from app.db.models import UserModel
from app.repositories.refresh_tokens import create_refresh_token
from fastapi.testclient import TestClient
from starlette.requests import Request

ATTEMPTS = 10
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class CapturingRedisClient:
    def __init__(self) -> None:
        self.keys: list[str] = []
        self.counts: dict[str, int] = {}

    def eval(self, script: str, numkeys: int, key: str, ttl_seconds: int):
        self.keys.append(key)
        count = self.counts.get(key, 0) + 1
        self.counts[key] = count
        return [count, ttl_seconds]


def _fresh_app(monkeypatch, *, redis_unavailable: bool = False):
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    config_module.get_settings.cache_clear()

    if redis_unavailable:
        monkeypatch.setattr(
            rate_limit_module,
            "_create_redis_client",
            lambda redis_url: (_ for _ in ()).throw(RateLimiterUnavailable()),
        )

    return importlib.reload(app_main_module).app


def _fresh_app_with_env(monkeypatch, **env_overrides: str | None):
    for key, value in env_overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    config_module.get_settings.cache_clear()
    return importlib.reload(app_main_module).app


@pytest.fixture()
def redis_unavailable_client(monkeypatch):
    app = _fresh_app(monkeypatch, redis_unavailable=True)
    with TestClient(app) as client:
        yield client


def _request(
    *,
    client_host: str = "10.0.0.10",
    headers: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def _register(db_client, email: str) -> None:
    response = db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201


def _assert_rate_limit_exceeded(response) -> None:
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(response.headers["Retry-After"]) > 0


def _disk_list(offsets: list[int]) -> list[dict[str, object]]:
    return [
        {"position": position, "sequence": _rotated_sequence(offset)}
        for position, offset in enumerate(offsets, start=1)
    ]


def _rotated_sequence(offset: int) -> str:
    offset = offset % len(ALPHABET)
    return ALPHABET[offset:] + ALPHABET[:offset]


def _auth_headers(user: UserModel) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _create_user(db_session, email: str) -> UserModel:
    user = UserModel(
        email=email,
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _disk_set_payload(slug: str) -> dict[str, object]:
    return {
        "name": slug.replace("-", " ").title(),
        "slug": slug,
        "alphabet": ALPHABET,
        "disks": _disk_list([0, 1, 2, 3]),
    }


def _cipher_payload() -> dict[str, object]:
    return {
        "text": "HELLOWORLD",
        "disk_set": {
            "alphabet": ALPHABET,
            "disks": [
                {"id": 1, "sequence": ALPHABET},
                {"id": 2, "sequence": _rotated_sequence(1)},
                {"id": 3, "sequence": _rotated_sequence(2)},
                {"id": 4, "sequence": _rotated_sequence(3)},
            ],
        },
        "key": {"disk_order": [1, 2, 3, 4], "offset": 2},
        "include_trace": True,
    }


def test_login_rate_limit_exceeded_returns_429(db_client) -> None:
    email = "login-rate-limit@example.com"
    _register(db_client, email)

    for _ in range(ATTEMPTS):
        db_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
        )

    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )

    _assert_rate_limit_exceeded(response)


def test_register_rate_limit_exceeded_returns_429(db_client) -> None:
    for index in range(ATTEMPTS):
        db_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"register-rate-limit-{index}@example.com",
                "password": "password123",
            },
        )

    response = db_client.post(
        "/api/v1/auth/register",
        json={
            "email": "register-rate-limit-final@example.com",
            "password": "password123",
        },
    )

    _assert_rate_limit_exceeded(response)


def test_refresh_rate_limit_exceeded_returns_429(db_session, db_client) -> None:
    user = _create_user(db_session, "refresh-rate-limit@example.com")

    for _ in range(ATTEMPTS):
        refresh_token = generate_refresh_token()
        create_refresh_token(
            db_session,
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_session.commit()

        db_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    final_refresh_token = generate_refresh_token()
    create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=hash_refresh_token(final_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.commit()

    response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": final_refresh_token},
    )

    _assert_rate_limit_exceeded(response)


def test_cipher_rate_limit_exceeded_returns_429(db_client) -> None:
    payload = _cipher_payload()

    for _ in range(ATTEMPTS):
        db_client.post("/api/v1/cipher/encrypt", json=payload)

    response = db_client.post("/api/v1/cipher/encrypt", json=payload)

    _assert_rate_limit_exceeded(response)


def test_disk_set_mutation_rate_limit_exceeded_returns_429(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "disk-set-rate-limit@example.com")

    for index in range(ATTEMPTS):
        db_client.post(
            "/api/v1/disk-sets",
            json=_disk_set_payload(f"rate-limit-set-{index}"),
            headers=_auth_headers(user),
        )

    response = db_client.post(
        "/api/v1/disk-sets",
        json=_disk_set_payload("rate-limit-set-final"),
        headers=_auth_headers(user),
    )

    _assert_rate_limit_exceeded(response)


def test_redis_limiter_state_is_shared_between_instances(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: 120.0)
    fake_redis = CapturingRedisClient()
    limiter_a = RedisRateLimiter(redis_url="redis://redis:6379/0", client=fake_redis)
    limiter_b = RedisRateLimiter(redis_url="redis://redis:6379/0", client=fake_redis)

    first = limiter_a.allow(bucket="auth", client_id="203.0.113.10", limit=1)
    second = limiter_b.allow(bucket="auth", client_id="203.0.113.10", limit=1)

    assert first.allowed is True
    assert second.allowed is False
    assert first.retry_after is None
    assert second.retry_after == 60


def test_memory_fallback_when_redis_url_is_empty(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    settings = config_module.Settings(REDIS_URL="", RATE_LIMIT_STORAGE="auto")

    limiter = get_rate_limiter(settings)

    assert isinstance(limiter, rate_limit_module.InMemoryRateLimiter)


def test_redis_unavailable_returns_503(redis_unavailable_client) -> None:
    response = redis_unavailable_client.post(
        "/api/v1/cipher/encrypt",
        json=_cipher_payload(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "RATE_LIMITER_UNAVAILABLE",
            "message": "Rate limiter unavailable",
        }
    }


def test_auto_storage_with_redis_url_and_redis_unavailable_returns_503(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        rate_limit_module,
        "_create_redis_client",
        lambda redis_url: (_ for _ in ()).throw(RateLimiterUnavailable()),
    )
    app = _fresh_app_with_env(
        monkeypatch,
        RATE_LIMIT_STORAGE="auto",
        REDIS_URL="redis://redis:6379/0",
        RATE_LIMIT_FAIL_OPEN="false",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/cipher/encrypt", json=_cipher_payload())

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "RATE_LIMITER_UNAVAILABLE",
            "message": "Rate limiter unavailable",
        }
    }


def test_redis_storage_fail_open_is_rejected(monkeypatch) -> None:
    with pytest.raises(
        ValueError,
        match="RATE_LIMIT_FAIL_OPEN is not allowed when Redis rate limiting is active",
    ):
        _fresh_app_with_env(
            monkeypatch,
            RATE_LIMIT_STORAGE="redis",
            REDIS_URL="redis://redis:6379/0",
            RATE_LIMIT_FAIL_OPEN="true",
        )


def test_redis_storage_without_url_is_rejected(monkeypatch) -> None:
    with pytest.raises(ValueError, match="RATE_LIMIT_STORAGE=redis requires REDIS_URL"):
        _fresh_app_with_env(
            monkeypatch,
            RATE_LIMIT_STORAGE="redis",
            REDIS_URL="",
            RATE_LIMIT_FAIL_OPEN="false",
        )


def test_rate_limit_keys_do_not_contain_secret_like_values(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: 120.0)
    fake_redis = CapturingRedisClient()
    limiter = RedisRateLimiter(redis_url="redis://redis:6379/0", client=fake_redis)
    request = _request(
        client_host="198.51.100.10",
        headers={
            "Authorization": "Bearer access-token-secret",
            "X-Forwarded-For": "198.51.100.20",
        },
    )
    settings = config_module.Settings()

    client_id = get_client_identifier(request, settings)
    limiter.allow(bucket="auth", client_id=client_id, limit=10)

    assert fake_redis.keys
    key = fake_redis.keys[0]
    assert "Authorization" not in key
    assert "access_token" not in key
    assert "refresh_token" not in key
    assert "password" not in key
    assert "body" not in key
    assert "access-token-secret" not in key


def test_reset_rate_limit_state_does_not_require_real_redis(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    called = False

    def _boom(redis_url: str):
        nonlocal called
        called = True
        raise AssertionError("unexpected redis client creation")

    monkeypatch.setattr(rate_limit_module, "_create_redis_client", _boom)

    rate_limit_module.reset_rate_limit_state()

    assert called is False


def test_proxy_headers_ignored_by_default() -> None:
    settings = config_module.Settings()
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "198.51.100.20"},
    )

    assert get_client_identifier(request, settings) == "10.0.0.10"


def test_proxy_headers_used_for_trusted_proxy(monkeypatch) -> None:
    settings = config_module.Settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS="10.0.0.10",
    )
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "198.51.100.20, 203.0.113.10"},
    )

    assert get_client_identifier(request, settings) == "198.51.100.20"


def test_proxy_headers_ignored_for_untrusted_direct_client() -> None:
    settings = config_module.Settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS="10.0.0.11",
    )
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "198.51.100.20"},
    )

    assert get_client_identifier(request, settings) == "10.0.0.10"


def test_malformed_proxy_headers_fall_back_safely() -> None:
    settings = config_module.Settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS="10.0.0.10",
    )
    request = _request(
        client_host="10.0.0.10",
        headers={"X-Forwarded-For": "not-an-ip, also-bad"},
    )

    assert get_client_identifier(request, settings) == "10.0.0.10"


def test_wildcard_trusted_proxy_is_explicit_escape_hatch() -> None:
    settings = config_module.Settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS="*",
    )
    request = _request(
        client_host="10.0.0.99",
        headers={"X-Forwarded-For": "198.51.100.20"},
    )

    assert get_client_identifier(request, settings) == "198.51.100.20"
