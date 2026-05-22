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
