from __future__ import annotations

import logging

from app.core.security import create_access_token, hash_password
from app.db.models import DiskModel, DiskSetModel, UserModel

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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


def _create_private_disk_set(db_session, owner_id: int, slug: str) -> DiskSetModel:
    disk_set = DiskSetModel(
        name=slug.replace("-", " ").title(),
        slug=slug,
        owner_id=owner_id,
        alphabet=ALPHABET,
        disks=[
            DiskModel(position=1, sequence=ALPHABET),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        ],
    )
    db_session.add(disk_set)
    db_session.commit()
    db_session.refresh(disk_set)
    return disk_set


def _log_messages(caplog) -> list[str]:
    return [record.getMessage().lower() for record in caplog.records]


def _joined_log_text(caplog) -> str:
    return "\n".join(_log_messages(caplog))


def _has_event(caplog, *candidates: str) -> bool:
    messages = _log_messages(caplog)
    return any(
        any(candidate.lower() in message for candidate in candidates)
        for message in messages
    )


def test_failed_login_emits_security_log_without_password(
    db_client, db_session, caplog
) -> None:
    user_email = "failed-login@example.com"
    _create_user(db_session, user_email)

    with caplog.at_level(logging.INFO):
        response = db_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert _has_event(caplog, "LOGIN_FAILURE", "auth.login.failure")
    assert user_email in _joined_log_text(caplog)
    assert "wrong-password" not in _joined_log_text(caplog)
    assert "access_token" not in _joined_log_text(caplog)
    assert "refresh_token" not in _joined_log_text(caplog)


def test_successful_login_emits_security_log_without_tokens(
    db_client, db_session, caplog
) -> None:
    user_email = "successful-login@example.com"
    _create_user(db_session, user_email)

    with caplog.at_level(logging.INFO):
        response = db_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "password123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert _has_event(caplog, "LOGIN_SUCCESS", "auth.login.success")
    assert body["access_token"] not in _joined_log_text(caplog)
    assert body["refresh_token"] not in _joined_log_text(caplog)


def test_refresh_replay_emits_security_log(db_client, db_session, caplog) -> None:
    user_email = "refresh-replay@example.com"
    _create_user(db_session, user_email)

    login_response = db_client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": "password123"},
    )
    assert login_response.status_code == 200
    old_refresh_token = login_response.json()["refresh_token"]

    refresh_response = db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert refresh_response.status_code == 200

    with caplog.at_level(logging.INFO):
        replay_response = db_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

    assert replay_response.status_code == 401
    assert _has_event(caplog, "REFRESH_REPLAY_DETECTED", "auth.refresh.replay")
    assert old_refresh_token not in _joined_log_text(caplog)


def test_denied_private_disk_set_access_emits_security_log(
    db_client, db_session, caplog
) -> None:
    owner = _create_user(db_session, "owner@example.com")
    other = _create_user(db_session, "other@example.com")
    disk_set = _create_private_disk_set(db_session, owner.id, "private-audit-set")

    with caplog.at_level(logging.INFO):
        response = db_client.get(
            f"/api/v1/disk-sets/{disk_set.id}",
            headers=_auth_headers(other),
        )

    assert response.status_code == 404
    assert _has_event(caplog, "DISK_SET_ACCESS_DENIED", "disk_set.access.denied")
    assert "private-audit-set" not in _joined_log_text(caplog)


def test_disk_set_mutation_emits_audit_log(db_client, db_session, caplog) -> None:
    user = _create_user(db_session, "audit-create@example.com")

    with caplog.at_level(logging.INFO):
        response = db_client.post(
            "/api/v1/disk-sets",
            json={
                "name": "Audit Create Set",
                "slug": "audit-create-set",
                "alphabet": ALPHABET,
                "disks": [
                    {"position": 1, "sequence": ALPHABET},
                    {"position": 2, "sequence": "BCDEFGHIJKLMNOPQRSTUVWXYZA"},
                    {"position": 3, "sequence": "CDEFGHIJKLMNOPQRSTUVWXYZAB"},
                    {"position": 4, "sequence": "DEFGHIJKLMNOPQRSTUVWXYZABC"},
                ],
            },
            headers=_auth_headers(user),
        )

    assert response.status_code == 201
    body = response.json()
    assert _has_event(caplog, "DISK_SET_CREATED", "disk_set.created")
    assert str(user.id) in _joined_log_text(caplog)
    assert str(body["id"]) in _joined_log_text(caplog)
    assert "password123" not in _joined_log_text(caplog)
    assert "access_token" not in _joined_log_text(caplog)
    assert "refresh_token" not in _joined_log_text(caplog)
