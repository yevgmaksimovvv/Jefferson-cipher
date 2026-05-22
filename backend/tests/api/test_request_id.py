from __future__ import annotations


def test_request_id_is_echoed_when_provided(client) -> None:
    response = client.get(
        "/api/v1/health", headers={"X-Request-ID": "smoke-request-id"}
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "smoke-request-id"


def test_request_id_is_generated_when_missing(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_request_id_is_present_on_404_response(client) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["X-Request-ID"]


def test_request_id_is_present_on_422_response(client) -> None:
    # Invalid login payload to trigger 422
    response = client.post("/api/v1/auth/login", json={"missing": "fields"})

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]


def test_existing_request_id_is_preserved_on_404(client) -> None:
    request_id = "preserve-me-404"
    response = client.get(
        "/api/v1/does-not-exist", headers={"X-Request-ID": request_id}
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == request_id


def test_existing_request_id_is_preserved_on_422(client) -> None:
    request_id = "preserve-me-422"
    response = client.post(
        "/api/v1/auth/login",
        json={"invalid": "payload"},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == request_id
