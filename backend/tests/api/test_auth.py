from __future__ import annotations

import jwt
from app.core.config import get_settings
from app.db.init_db import seed_default_disk_set
from app.db.models import UserModel
from sqlalchemy import select


def test_register_creates_user_and_hides_password(db_session, db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/register",
        json={
            "email": "  New.User@Example.com  ",
            "password": "secret-password",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["is_active"] is True
    assert "hashed_password" not in body

    user = db_session.scalar(
        select(UserModel).where(UserModel.email == "new.user@example.com")
    )
    assert user is not None
    assert user.hashed_password != "secret-password"


def test_register_lowercases_and_strips_email(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/register",
        json={"email": "  MIXED.CASE@Example.com ", "password": "password123"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "mixed.case@example.com"


def test_duplicate_register_returns_409_stable_error_shape(db_client) -> None:
    payload = {"email": "duplicate@example.com", "password": "password123"}
    first_response = db_client.post("/api/v1/auth/register", json=payload)
    assert first_response.status_code == 201

    second_response = db_client.post("/api/v1/auth/register", json=payload)

    assert second_response.status_code == 409
    assert second_response.json() == {
        "error": {
            "code": "EMAIL_ALREADY_REGISTERED",
            "message": "Email already registered",
        }
    }


def test_login_with_correct_password_returns_bearer_token(db_client) -> None:
    db_client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )

    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401_stable_error_shape(db_client) -> None:
    db_client.post(
        "/api/v1/auth/register",
        json={"email": "wrong-password@example.com", "password": "password123"},
    )

    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "wrong-password@example.com", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password",
        }
    }


def test_login_with_unknown_email_returns_401_stable_error_shape(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password",
        }
    }


def test_access_token_has_decodable_sub_and_exp(db_session, db_client) -> None:
    db_client.post(
        "/api/v1/auth/register",
        json={"email": "token@example.com", "password": "password123"},
    )

    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "token@example.com", "password": "password123"},
    )

    token = response.json()["access_token"]
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
    )
    user = db_session.scalar(
        select(UserModel).where(UserModel.email == "token@example.com")
    )
    assert user is not None

    assert claims["sub"] == str(user.id)
    assert claims["exp"] is not None


def test_public_disk_sets_and_cipher_endpoints_still_work_without_auth(
    db_session, db_client
) -> None:
    seed_default_disk_set(db_session)

    disk_sets_response = db_client.get("/api/v1/disk-sets")
    assert disk_sets_response.status_code == 200

    cipher_response = db_client.post(
        "/api/v1/cipher/encrypt",
        json={
            "text": "Hello, World! 123",
            "disk_set": {
                "alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "disks": [
                    {"id": 1, "sequence": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
                    {"id": 2, "sequence": "BCDEFGHIJKLMNOPQRSTUVWXYZA"},
                    {"id": 3, "sequence": "CDEFGHIJKLMNOPQRSTUVWXYZAB"},
                    {"id": 4, "sequence": "DEFGHIJKLMNOPQRSTUVWXYZABC"},
                ],
            },
            "key": {"disk_order": [1, 2, 3, 4], "offset": 2},
        },
    )

    assert cipher_response.status_code == 200
    assert cipher_response.json()["text"] == "JGNNQYQTNF"
