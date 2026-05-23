from __future__ import annotations

import importlib

import app.main as app_main_module
import pytest
from app.core import config as config_module
from fastapi.testclient import TestClient


def _assert_security_headers(response) -> None:
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy")


@pytest.fixture()
def hsts_client(monkeypatch):
    monkeypatch.setenv("ENABLE_HSTS", "true")
    monkeypatch.setenv("HSTS_MAX_AGE_SECONDS", "123")
    config_module.get_settings.cache_clear()
    app = importlib.reload(app_main_module).app
    with TestClient(app) as client:
        yield client


def test_cors_preflight_allows_localhost_5173(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in (200, 204)
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )


def test_cors_preflight_allows_localhost_8443(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://localhost:8443",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in (200, 204)
    assert (
        response.headers.get("access-control-allow-origin") == "https://localhost:8443"
    )


def test_cors_preflight_rejects_unknown_origin(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "http://evil.example"


def test_cors_does_not_use_wildcard_by_default(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "*"


def test_cors_wildcard_origin_is_rejected_by_settings() -> None:
    with pytest.raises(
        ValueError, match="BACKEND_CORS_ORIGINS must not contain wildcard \\*"
    ):
        config_module.Settings(BACKEND_CORS_ORIGINS=["*"])


def test_security_headers_present_on_health(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    _assert_security_headers(response)
    assert "strict-transport-security" not in response.headers


def test_security_headers_present_on_error_response(client) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    _assert_security_headers(response)


def test_hsts_header_is_opt_in(hsts_client) -> None:
    response = hsts_client.get("/api/v1/health")

    assert response.status_code == 200
    _assert_security_headers(response)
    assert (
        response.headers.get("strict-transport-security")
        == "max-age=123; includeSubDomains"
    )


def test_existing_security_headers_remain_with_hsts(hsts_client) -> None:
    response = hsts_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    _assert_security_headers(response)
    assert response.headers.get("strict-transport-security") == (
        "max-age=123; includeSubDomains"
    )
