def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "jefferson-cipher-service",
        "version": "0.1.0",
    }
