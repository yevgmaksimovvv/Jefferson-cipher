from __future__ import annotations

import re

from app.core.security import hash_password
from app.db.init_db import seed_default_disk_set
from app.db.models import DiskModel, DiskSetModel, UserModel


def _create_user(db_session, email: str, password: str = "password123") -> UserModel:
    user = UserModel(
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_compact_public_disk_set(db_session) -> DiskSetModel:
    disk_set = DiskSetModel(
        name="Compact Public Set",
        slug="compact-public-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        ],
    )
    db_session.add(disk_set)
    db_session.commit()
    db_session.refresh(disk_set)
    return disk_set


def _cipher_payload(
    *,
    disk_set_id: int,
    text: str = "HELLOWORLD",
    include_trace: bool = True,
    disk_order: str = "1,2,3,4",
    offset: str = "2",
    mode: str = "encrypt",
) -> dict[str, str]:
    return {
        "mode": mode,
        "text": text,
        "disk_set_id": str(disk_set_id),
        "disk_order": disk_order,
        "offset": offset,
        "include_trace": "on" if include_trace else "",
    }


def _csrf_token_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_cipher_page_anonymous_shows_public_disk_set(db_session, db_client) -> None:
    seed_default_disk_set(db_session)

    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "Jefferson Standard" in response.text
    assert "system" in response.text


def test_cipher_page_authenticated_shows_private_disk_set(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "cipher-owner@example.com")
    login_page = db_client.get("/login")
    csrf_token = _csrf_token_from_html(login_page.text)
    db_client.post(
        "/login",
        data={
            "email": user.email,
            "password": "password123",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    db_session.add(
        DiskSetModel(
            name="Private Set",
            slug="private-set",
            owner_id=user.id,
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            disks=[
                DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
                DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
                DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
            ],
        )
    )
    db_session.commit()

    response = db_client.get("/cipher")

    assert response.status_code == 200
    assert "Private Set" in response.text
    assert "private" in response.text


def test_cipher_encrypt_and_decrypt_round_trip(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    encrypt_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id, mode="encrypt"),
            "csrf_token": csrf_token,
        },
    )

    assert encrypt_response.status_code == 200
    assert "JGNNQYQTNF" in encrypt_response.text
    assert "Normalized text" in encrypt_response.text
    assert "access_token" not in encrypt_response.text
    assert "refresh_token" not in encrypt_response.text

    decrypt_response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(
                disk_set_id=disk_set.id,
                text="JGNNQYQTNF",
                mode="decrypt",
            ),
            "csrf_token": csrf_token,
        },
    )

    assert decrypt_response.status_code == 200
    assert "HELLOWORLD" in decrypt_response.text


def test_cipher_invalid_form_shows_error_and_does_not_500(
    db_session, db_client
) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id, disk_order="abc"),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert "Disk order must contain only numbers" in response.text
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def test_cipher_result_page_does_not_render_tokens(db_session, db_client) -> None:
    disk_set = _create_compact_public_disk_set(db_session)
    cipher_page = db_client.get("/cipher")
    csrf_token = _csrf_token_from_html(cipher_page.text)

    response = db_client.post(
        "/cipher",
        data={
            **_cipher_payload(disk_set_id=disk_set.id),
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
