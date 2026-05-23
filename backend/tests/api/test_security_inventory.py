from __future__ import annotations

from pathlib import Path

EXPECTED_PATHS = {
    "/api/v1/health": {"get"},
    "/api/v1/ready": {"get"},
    "/api/v1/auth/register": {"post"},
    "/api/v1/auth/login": {"post"},
    "/api/v1/auth/refresh": {"post"},
    "/api/v1/auth/logout": {"post"},
    "/api/v1/users/me": {"get"},
    "/api/v1/cipher/encrypt": {"post"},
    "/api/v1/cipher/decrypt": {"post"},
    "/api/v1/cipher/encrypt/from-disk-set": {"post"},
    "/api/v1/cipher/decrypt/from-disk-set": {"post"},
    "/api/v1/disk-sets": {"get", "post"},
    "/api/v1/disk-sets/{disk_set_id}": {"get", "patch", "delete"},
}

OPTIONAL_AUTH_PATHS = {
    "/api/v1/disk-sets",
    "/api/v1/disk-sets/{disk_set_id}",
    "/api/v1/cipher/encrypt/from-disk-set",
    "/api/v1/cipher/decrypt/from-disk-set",
}

AUTH_REQUIRED_OPERATIONS = {
    "/api/v1/users/me": {"get"},
    "/api/v1/disk-sets": {"post"},
    "/api/v1/disk-sets/{disk_set_id}": {"patch", "delete"},
}

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/cipher/encrypt",
    "/api/v1/cipher/decrypt",
    "/api/v1/cipher/encrypt/from-disk-set",
    "/api/v1/cipher/decrypt/from-disk-set",
    "/api/v1/disk-sets",
    "/api/v1/disk-sets/{disk_set_id}",
}

FORBIDDEN_PATH_TOKENS = (
    "debug",
    "admin",
    "internal",
    "metrics",
    "test",
    "dev",
    "playground",
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def _operation_security(operation: dict[str, object]) -> object:
    return operation.get("security")


def test_openapi_inventory_matches_expected_paths_and_methods(client) -> None:
    schema = client.app.openapi()

    assert set(schema["paths"]) == set(EXPECTED_PATHS)
    assert [tag["name"] for tag in schema["tags"]] == [
        "health",
        "auth",
        "users",
        "cipher",
        "disk-sets",
    ]

    for path, expected_methods in EXPECTED_PATHS.items():
        operation_methods = {
            method for method in schema["paths"][path] if method in HTTP_METHODS
        }
        assert operation_methods == expected_methods

    for path, operations in schema["paths"].items():
        lowered_path = path.lower()
        assert not any(token in lowered_path for token in FORBIDDEN_PATH_TOKENS)
        for method, operation in operations.items():
            if method not in HTTP_METHODS:
                continue
            if (
                path in AUTH_REQUIRED_OPERATIONS
                and method in AUTH_REQUIRED_OPERATIONS[path]
            ):
                assert _operation_security(operation) == [{"OAuth2PasswordBearer": []}]
            elif path in PUBLIC_PATHS or path in OPTIONAL_AUTH_PATHS:
                assert _operation_security(operation) in (None, [])


def test_openapi_inventory_keeps_business_and_tooling_routes_separate(client) -> None:
    schema = client.app.openapi()

    assert "/docs" not in schema["paths"]
    assert "/redoc" not in schema["paths"]
    assert "/openapi.json" not in schema["paths"]


def test_openapi_docs_reference_security_contract_terms() -> None:
    docs = (Path(__file__).resolve().parents[3] / "docs" / "api.md").read_text(
        encoding="utf-8"
    )
    lowered = docs.lower()

    for path in EXPECTED_PATHS:
        assert path in docs

    assert "204" in docs
    assert "401" in docs
    assert "404" in docs
    assert "422" in docs
    assert "429" in docs
    assert "503" in docs
    assert "owner_id" in lowered
    assert ("не принимается" in lowered) or ("not accepted" in lowered)
    assert "limit" in lowered
    assert "offset" in lowered
    assert "redis" in lowered
    assert "rate limit" in lowered
    assert ("runtime.md" in lowered) or ("8443" in lowered)
