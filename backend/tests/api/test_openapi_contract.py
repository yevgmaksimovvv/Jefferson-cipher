from __future__ import annotations

from pathlib import Path

EXPECTED_PATHS = {
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/users/me",
    "/api/v1/cipher/encrypt",
    "/api/v1/cipher/decrypt",
    "/api/v1/cipher/encrypt/from-disk-set",
    "/api/v1/cipher/decrypt/from-disk-set",
    "/api/v1/disk-sets",
    "/api/v1/disk-sets/{disk_set_id}",
}

EXPECTED_TAGS = ["health", "auth", "users", "cipher", "disk-sets"]

DOCS_PATH = Path(__file__).resolve().parents[3] / "docs" / "api.md"


def test_openapi_contract_matches_expected_routes_and_tags(client) -> None:
    schema = client.app.openapi()

    assert schema["info"]["title"] == "Jefferson Cipher Service"
    assert schema["info"]["version"] == "0.1.0"
    assert "persisted disk sets" in schema["info"]["description"]
    assert "JWT auth + refresh tokens" in schema["info"]["description"]
    assert "rate limiting" in schema["info"]["description"]
    assert "readiness endpoint" in schema["info"]["description"]

    assert [tag["name"] for tag in schema["tags"]] == EXPECTED_TAGS

    assert EXPECTED_PATHS.issubset(schema["paths"].keys())

    logout_responses = schema["paths"]["/api/v1/auth/logout"]["post"]["responses"]
    delete_responses = schema["paths"]["/api/v1/disk-sets/{disk_set_id}"]["delete"][
        "responses"
    ]

    assert "204" in logout_responses
    assert "200" not in logout_responses
    assert "204" in delete_responses
    assert "200" not in delete_responses

    create_properties = schema["components"]["schemas"]["DiskSetCreateRequest"][
        "properties"
    ]
    update_properties = schema["components"]["schemas"]["DiskSetUpdateRequest"][
        "properties"
    ]

    assert "owner_id" not in create_properties
    assert "owner_id" not in update_properties

    list_params = schema["paths"]["/api/v1/disk-sets"]["get"]["parameters"]
    params_by_name = {param["name"]: param for param in list_params}

    assert params_by_name["limit"]["schema"]["default"] == 50
    assert params_by_name["limit"]["schema"]["maximum"] == 100
    assert params_by_name["limit"]["schema"]["minimum"] == 1
    assert params_by_name["offset"]["schema"]["default"] == 0
    assert params_by_name["offset"]["schema"]["minimum"] == 0


def test_openapi_docs_reference_contract_terms() -> None:
    docs = DOCS_PATH.read_text(encoding="utf-8")
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
