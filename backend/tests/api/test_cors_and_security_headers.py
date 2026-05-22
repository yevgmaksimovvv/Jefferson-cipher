from __future__ import annotations


def _assert_security_headers(response) -> None:
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy")


def test_cors_preflight_allows_configured_origin(client) -> None:
    # Bearer auth is used, so credentials are not required; the contract is origin echo.
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


def test_cors_preflight_rejects_unknown_origin(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "http://evil.example"


def test_security_headers_present_on_health(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    _assert_security_headers(response)


def test_security_headers_present_on_error_response(client) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    _assert_security_headers(response)
