from __future__ import annotations

from app.core.security import create_access_token
from app.services.auth import register_user


def test_users_me_without_token_returns_401(db_client) -> None:
    response = db_client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_users_me_with_invalid_token_returns_401(db_client) -> None:
    response = db_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_users_me_with_valid_token_returns_current_user(db_session, db_client) -> None:
    user = register_user(db_session, "me@example.com", "password123")
    token = create_access_token(str(user.id))

    response = db_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "me@example.com",
        "is_active": True,
    }


def test_users_me_with_missing_user_token_returns_401(db_client) -> None:
    token = create_access_token("999999")

    response = db_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_users_me_with_inactive_user_returns_401(db_session, db_client) -> None:
    user = register_user(db_session, "inactive@example.com", "password123")
    user.is_active = False
    db_session.commit()

    token = create_access_token(str(user.id))
    response = db_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
