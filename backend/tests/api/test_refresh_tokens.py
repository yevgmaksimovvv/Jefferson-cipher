from __future__ import annotations

from datetime import datetime, timedelta

from app.core.security import generate_refresh_token, hash_refresh_token
from app.db.models import RefreshTokenModel, UserModel
from app.repositories.refresh_tokens import create_refresh_token
from app.services.auth import register_user
from sqlalchemy import select


def _register_and_login(db_client, email: str = "refresh@example.com"):
    register_response = db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = db_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    return login_response.json()


def test_refresh_rotates_token_pair_and_old_token_is_invalidated(
    db_session, db_client
) -> None:
    token_pair = _register_and_login(db_client, "rotate@example.com")
    old_refresh_token = token_pair["refresh_token"]

    refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert refresh_response.status_code == 200
    refresh_body = refresh_response.json()
    assert refresh_body["token_type"] == "bearer"
    assert refresh_body["access_token"]
    assert refresh_body["refresh_token"]
    assert refresh_body["refresh_token"] != old_refresh_token

    old_refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert old_refresh_response.status_code == 401
    assert old_refresh_response.json() == {
        "error": {
            "code": "INVALID_REFRESH_TOKEN",
            "message": "Invalid refresh token",
        }
    }
    assert old_refresh_response.headers["www-authenticate"] == "Bearer"

    user = db_session.scalar(
        select(UserModel).where(UserModel.email == "rotate@example.com")
    )
    assert user is not None

    me_response = db_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "rotate@example.com"


def test_refresh_db_stores_only_token_hash_and_rotated_link(
    db_session, db_client
) -> None:
    token_pair = _register_and_login(db_client, "hash@example.com")
    plain_refresh_token = token_pair["refresh_token"]
    token_hash = hash_refresh_token(plain_refresh_token)

    row = db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
    )
    assert row is not None
    assert row.token_hash != plain_refresh_token
    assert len(row.token_hash) == 64

    refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": plain_refresh_token},
    )
    assert refresh_response.status_code == 200

    new_plain_refresh_token = refresh_response.json()["refresh_token"]
    old_row = db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
    )
    assert old_row is not None
    db_session.refresh(old_row)
    assert old_row.revoked_at is not None

    new_row = db_session.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == hash_refresh_token(new_plain_refresh_token)
        )
    )
    assert new_row is not None
    db_session.refresh(new_row)
    assert new_row.revoked_at is None
    assert old_row.replaced_by_token_id == new_row.id


def test_refresh_with_empty_token_returns_401(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ""},
    )

    # Current service returns 401 for unknown/empty token
    assert response.status_code == 401


def test_refresh_response_does_not_contain_token_hash(db_client) -> None:
    token_pair = _register_and_login(db_client, "no-hash@example.com")

    refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert "token_hash" not in body


def test_logout_twice_with_same_refresh_token_returns_401_on_second(db_client) -> None:
    token_pair = _register_and_login(db_client, "logout-twice@example.com")
    refresh_token = token_pair["refresh_token"]

    first_logout = db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert first_logout.status_code == 204

    second_logout = db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert second_logout.status_code == 401


def test_logout_response_body_is_empty_on_204(db_client) -> None:
    token_pair = _register_and_login(db_client, "empty-body@example.com")

    response = db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": token_pair["refresh_token"]},
    )

    assert response.status_code == 204
    assert response.content == b""


def test_refresh_with_random_token_returns_401(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "INVALID_REFRESH_TOKEN",
            "message": "Invalid refresh token",
        }
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_refresh_with_expired_token_returns_401(db_session, db_client) -> None:
    user = register_user(db_session, "expired@example.com", "password123")
    plain_refresh_token = generate_refresh_token()
    create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=hash_refresh_token(plain_refresh_token),
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.commit()

    response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": plain_refresh_token},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "INVALID_REFRESH_TOKEN",
            "message": "Invalid refresh token",
        }
    }


def test_refresh_with_inactive_user_returns_401(db_session, db_client) -> None:
    user = register_user(db_session, "inactive@example.com", "password123")
    user.is_active = False
    db_session.commit()

    plain_refresh_token = generate_refresh_token()
    create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=hash_refresh_token(plain_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.commit()

    response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": plain_refresh_token},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "INVALID_REFRESH_TOKEN",
            "message": "Invalid refresh token",
        }
    }


def test_logout_with_valid_refresh_token_revokes_it(db_client) -> None:
    token_pair = _register_and_login(db_client, "logout@example.com")
    refresh_token = token_pair["refresh_token"]

    response = db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 204
    assert response.content == b""

    refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_logout_with_invalid_refresh_token_returns_401(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "INVALID_REFRESH_TOKEN",
            "message": "Invalid refresh token",
        }
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_logout_openapi_declares_204(db_client) -> None:
    openapi = db_client.app.openapi()
    responses = openapi["paths"]["/api/v1/auth/logout"]["post"]["responses"]

    assert "204" in responses
    assert "200" not in responses
