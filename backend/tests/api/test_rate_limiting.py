from __future__ import annotations

from datetime import datetime, timedelta

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
)
from app.db.models import UserModel
from app.repositories.refresh_tokens import create_refresh_token

ATTEMPTS = 10
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _rotated_sequence(offset: int) -> str:
    offset = offset % len(ALPHABET)
    return ALPHABET[offset:] + ALPHABET[:offset]


def _disk_list(offsets: list[int]) -> list[dict[str, object]]:
    return [
        {"position": position, "sequence": _rotated_sequence(offset)}
        for position, offset in enumerate(offsets, start=1)
    ]


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


def _register(db_client, email: str) -> None:
    response = db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201


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

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


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

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


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

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_cipher_rate_limit_exceeded_returns_429(db_client) -> None:
    payload = _cipher_payload()

    for _ in range(ATTEMPTS):
        db_client.post("/api/v1/cipher/encrypt", json=payload)

    response = db_client.post("/api/v1/cipher/encrypt", json=payload)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


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

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
