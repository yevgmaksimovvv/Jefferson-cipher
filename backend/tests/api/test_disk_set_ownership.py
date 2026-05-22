from __future__ import annotations

from app.core.security import create_access_token
from app.db.models import DiskModel, DiskSetModel, UserModel


def _disk_set(slug: str, owner_id: int | None = None) -> DiskSetModel:
    return DiskSetModel(
        name=slug.replace("-", " ").title(),
        slug=slug,
        owner_id=owner_id,
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        ],
    )


def _cipher_payload(
    *,
    disk_set_id: int,
    text: str = "HELLOWORLD",
    include_trace: bool = True,
) -> dict:
    return {
        "text": text,
        "disk_set_id": disk_set_id,
        "key": {
            "disk_order": [1, 2, 3, 4],
            "offset": 2,
        },
        "include_trace": include_trace,
    }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user(db_session, email: str) -> UserModel:
    user = UserModel(
        email=email,
        hashed_password="hashed-password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_disk_set(
    db_session, slug: str, owner_id: int | None = None
) -> DiskSetModel:
    disk_set = _disk_set(slug, owner_id=owner_id)
    db_session.add(disk_set)
    db_session.commit()
    db_session.refresh(disk_set)
    return disk_set


def test_anonymous_get_disk_sets_sees_public_only(db_session, db_client) -> None:
    _create_disk_set(db_session, "public-set")
    _create_disk_set(
        db_session,
        "private-set-a",
        owner_id=_create_user(db_session, "a@example.com").id,
    )
    _create_disk_set(
        db_session,
        "private-set-b",
        owner_id=_create_user(db_session, "b@example.com").id,
    )

    response = db_client.get("/api/v1/disk-sets")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == ["public-set"]


def test_user_a_get_disk_sets_sees_public_and_own_private(
    db_session, db_client
) -> None:
    user_a = _create_user(db_session, "a@example.com")
    user_b = _create_user(db_session, "b@example.com")
    _create_disk_set(db_session, "public-set")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)
    _create_disk_set(db_session, "private-set-b", owner_id=user_b.id)

    response = db_client.get(
        "/api/v1/disk-sets",
        headers=_auth_headers(create_access_token(str(user_a.id))),
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == [
        "public-set",
        "private-set-a",
    ]
    assert private_a.id is not None


def test_user_b_get_disk_sets_sees_public_and_own_private(
    db_session, db_client
) -> None:
    user_a = _create_user(db_session, "a@example.com")
    user_b = _create_user(db_session, "b@example.com")
    _create_disk_set(db_session, "public-set")
    _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)
    _create_disk_set(db_session, "private-set-b", owner_id=user_b.id)

    response = db_client.get(
        "/api/v1/disk-sets",
        headers=_auth_headers(create_access_token(str(user_b.id))),
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == [
        "public-set",
        "private-set-b",
    ]


def test_anonymous_get_private_disk_set_returns_404(db_session, db_client) -> None:
    user_a = _create_user(db_session, "a@example.com")
    _create_disk_set(db_session, "public-set")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.get(f"/api/v1/disk-sets/{private_a.id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "DISK_SET_NOT_FOUND",
            "message": "Disk set not found",
        }
    }


def test_user_a_get_own_private_disk_set_returns_200(db_session, db_client) -> None:
    user_a = _create_user(db_session, "a@example.com")
    _create_disk_set(db_session, "public-set")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.get(
        f"/api/v1/disk-sets/{private_a.id}",
        headers=_auth_headers(create_access_token(str(user_a.id))),
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "private-set-a"


def test_user_b_get_foreign_private_disk_set_returns_404(db_session, db_client) -> None:
    user_a = _create_user(db_session, "a@example.com")
    user_b = _create_user(db_session, "b@example.com")
    _create_disk_set(db_session, "public-set")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.get(
        f"/api/v1/disk-sets/{private_a.id}",
        headers=_auth_headers(create_access_token(str(user_b.id))),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_anonymous_can_encrypt_from_public_disk_set(db_session, db_client) -> None:
    public_disk_set = _create_disk_set(db_session, "public-set")

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=public_disk_set.id),
    )

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"


def test_anonymous_cannot_encrypt_from_private_disk_set(db_session, db_client) -> None:
    user_a = _create_user(db_session, "a@example.com")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=private_a.id),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_user_a_can_encrypt_from_own_private_disk_set(db_session, db_client) -> None:
    user_a = _create_user(db_session, "a@example.com")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=private_a.id),
        headers=_auth_headers(create_access_token(str(user_a.id))),
    )

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"


def test_user_b_cannot_encrypt_from_user_a_private_disk_set(
    db_session, db_client
) -> None:
    user_a = _create_user(db_session, "a@example.com")
    user_b = _create_user(db_session, "b@example.com")
    private_a = _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=private_a.id),
        headers=_auth_headers(create_access_token(str(user_b.id))),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_optional_auth_endpoint_rejects_invalid_token(db_session, db_client) -> None:
    _create_disk_set(db_session, "public-set")

    response = db_client.get(
        "/api/v1/disk-sets",
        headers=_auth_headers("not-a-valid-token"),
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_get_specific_disk_set_with_invalid_token_returns_401(
    db_session, db_client
) -> None:
    public_disk_set = _create_disk_set(db_session, "public-set")

    response = db_client.get(
        f"/api/v1/disk-sets/{public_disk_set.id}",
        headers=_auth_headers("not-a-valid-token"),
    )

    assert response.status_code == 401


def test_encrypt_from_disk_set_with_invalid_token_returns_401(
    db_session, db_client
) -> None:
    public_disk_set = _create_disk_set(db_session, "public-set")

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=public_disk_set.id),
        headers=_auth_headers("not-a-valid-token"),
    )

    assert response.status_code == 401


def test_decrypt_from_disk_set_with_invalid_token_returns_401(
    db_session, db_client
) -> None:
    public_disk_set = _create_disk_set(db_session, "public-set")

    response = db_client.post(
        "/api/v1/cipher/decrypt/from-disk-set",
        json=_cipher_payload(disk_set_id=public_disk_set.id),
        headers=_auth_headers("not-a-valid-token"),
    )

    assert response.status_code == 401


def test_optional_auth_endpoint_treats_missing_token_as_anonymous(
    db_session, db_client
) -> None:
    _create_disk_set(db_session, "public-set")
    user_a = _create_user(db_session, "a@example.com")
    _create_disk_set(db_session, "private-set-a", owner_id=user_a.id)

    response = db_client.get("/api/v1/disk-sets")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == ["public-set"]


def test_stateless_encrypt_still_works_without_token(client) -> None:
    response = client.post(
        "/api/v1/cipher/encrypt",
        json={
            "text": "HELLOWORLD",
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

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"


def test_stateless_decrypt_still_works_without_token(client) -> None:
    encrypt_response = client.post(
        "/api/v1/cipher/encrypt",
        json={
            "text": "HELLOWORLD",
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
    ciphertext = encrypt_response.json()["text"]

    response = client.post(
        "/api/v1/cipher/decrypt",
        json={
            "text": ciphertext,
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

    assert response.status_code == 200
    assert response.json()["text"] == "HELLOWORLD"
