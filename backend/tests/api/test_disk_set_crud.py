from __future__ import annotations

from app.core.security import create_access_token
from app.db.init_db import seed_default_disk_set
from app.db.models import DiskSetModel, UserModel
from sqlalchemy import select

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _rotated_sequence(offset: int) -> str:
    offset = offset % len(ALPHABET)
    return ALPHABET[offset:] + ALPHABET[:offset]


def _disk_list(offsets: list[int]) -> list[dict[str, object]]:
    return [
        {"position": position, "sequence": _rotated_sequence(offset)}
        for position, offset in enumerate(offsets, start=1)
    ]


def _base_payload() -> dict[str, object]:
    return {
        "name": "Owned Set",
        "slug": "owned-set",
        "alphabet": ALPHABET,
        "disks": _disk_list([0, 1, 2, 3]),
    }


def _replacement_disks() -> list[dict[str, object]]:
    return _disk_list([4, 5, 6, 7])


def _auth_headers(user: UserModel) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


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
    db_client,
    user: UserModel,
    payload: dict[str, object] | None = None,
):
    response = db_client.post(
        "/api/v1/disk-sets",
        json=payload or _base_payload(),
        headers=_auth_headers(user),
    )
    return response


def _owned_disk_set_model(db_session, disk_set_id: int) -> DiskSetModel | None:
    return db_session.scalar(select(DiskSetModel).where(DiskSetModel.id == disk_set_id))


def test_anonymous_post_disk_sets_returns_401(db_client) -> None:
    response = db_client.post("/api/v1/disk-sets", json=_base_payload())

    assert response.status_code == 401


def test_authenticated_post_creates_private_disk_set(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")

    response = _create_disk_set(db_client, user)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Owned Set"
    assert body["slug"] == "owned-set"
    assert [disk["position"] for disk in body["disks"]] == [1, 2, 3, 4]
    assert [disk["sequence"] for disk in body["disks"]] == [
        ALPHABET,
        _rotated_sequence(1),
        _rotated_sequence(2),
        _rotated_sequence(3),
    ]

    disk_set = _owned_disk_set_model(db_session, body["id"])
    assert disk_set is not None
    assert disk_set.owner_id == user.id


def test_created_disk_set_appears_in_owner_list(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.get(
        "/api/v1/disk-sets",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == [created["slug"]]


def test_created_disk_set_does_not_appear_in_other_user_list(
    db_session, db_client
) -> None:
    owner = _create_user(db_session, "owner@example.com")
    other = _create_user(db_session, "other@example.com")
    _create_disk_set(db_client, owner)

    response = db_client.get(
        "/api/v1/disk-sets",
        headers=_auth_headers(other),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_owner_get_own_private_disk_set_returns_200(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.get(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "owned-set"


def test_other_user_get_foreign_private_disk_set_returns_404(
    db_session, db_client
) -> None:
    owner = _create_user(db_session, "owner@example.com")
    other = _create_user(db_session, "other@example.com")
    created = _create_disk_set(db_client, owner).json()

    response = db_client.get(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(other),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_owner_patch_name_and_slug_returns_200(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"name": "Updated Name", "slug": "updated-slug"},
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Name"
    assert body["slug"] == "updated-slug"


def test_owner_patch_disks_replaces_full_list(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"disks": _replacement_disks()},
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert [disk["position"] for disk in body["disks"]] == [1, 2, 3, 4]
    assert [disk["sequence"] for disk in body["disks"]] == [
        _rotated_sequence(4),
        _rotated_sequence(5),
        _rotated_sequence(6),
        _rotated_sequence(7),
    ]

    disk_set = _owned_disk_set_model(db_session, created["id"])
    assert disk_set is not None
    assert len(disk_set.disks) == 4
    assert [disk.position for disk in disk_set.disks] == [1, 2, 3, 4]
    assert [disk.sequence for disk in disk_set.disks] == [
        _rotated_sequence(4),
        _rotated_sequence(5),
        _rotated_sequence(6),
        _rotated_sequence(7),
    ]


def test_other_user_patch_returns_404(db_session, db_client) -> None:
    owner = _create_user(db_session, "owner@example.com")
    other = _create_user(db_session, "other@example.com")
    created = _create_disk_set(db_client, owner).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"name": "Denied"},
        headers=_auth_headers(other),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_anonymous_patch_returns_401(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"name": "Denied"},
    )

    assert response.status_code == 401


def test_owner_delete_returns_204_with_empty_body(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.delete(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(user),
    )

    assert response.status_code == 204
    assert response.content == b""


def test_deleted_disk_set_is_not_gettable(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    delete_response = db_client.delete(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(user),
    )
    assert delete_response.status_code == 204

    response = db_client.get(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_other_user_delete_returns_404(db_session, db_client) -> None:
    owner = _create_user(db_session, "owner@example.com")
    other = _create_user(db_session, "other@example.com")
    created = _create_disk_set(db_client, owner).json()

    response = db_client.delete(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(other),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_anonymous_delete_returns_401(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.delete(f"/api/v1/disk-sets/{created['id']}")

    assert response.status_code == 401


def test_public_jefferson_standard_patch_returns_404(db_session, db_client) -> None:
    disk_set = seed_default_disk_set(db_session)
    user = _create_user(db_session, "owner@example.com")

    response = db_client.patch(
        f"/api/v1/disk-sets/{disk_set.id}",
        json={"name": "Updated Name"},
        headers=_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_public_jefferson_standard_delete_returns_404(db_session, db_client) -> None:
    disk_set = seed_default_disk_set(db_session)
    user = _create_user(db_session, "owner@example.com")

    response = db_client.delete(
        f"/api/v1/disk-sets/{disk_set.id}",
        headers=_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"


def test_duplicate_slug_on_create_returns_409(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    _create_disk_set(
        db_client,
        user,
        {
            "name": "First",
            "slug": "duplicate-slug",
            "alphabet": ALPHABET,
            "disks": _disk_list([0, 1, 2, 3]),
        },
    )

    response = db_client.post(
        "/api/v1/disk-sets",
        json={
            "name": "Second",
            "slug": "duplicate-slug",
            "alphabet": ALPHABET,
            "disks": _disk_list([4, 5, 6, 7]),
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DISK_SET_SLUG_ALREADY_EXISTS"


def test_duplicate_slug_on_patch_returns_409(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    first = _create_disk_set(
        db_client,
        user,
        {
            "name": "First",
            "slug": "first-slug",
            "alphabet": ALPHABET,
            "disks": _disk_list([0, 1, 2, 3]),
        },
    ).json()
    second = _create_disk_set(
        db_client,
        user,
        {
            "name": "Second",
            "slug": "second-slug",
            "alphabet": ALPHABET,
            "disks": _disk_list([4, 5, 6, 7]),
        },
    ).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{second['id']}",
        json={"slug": first["slug"]},
        headers=_auth_headers(user),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DISK_SET_SLUG_ALREADY_EXISTS"


def test_invalid_disk_sequence_on_create_returns_400(db_client, db_session) -> None:
    user = _create_user(db_session, "owner@example.com")

    response = db_client.post(
        "/api/v1/disk-sets",
        json={
            "name": "Broken",
            "slug": "broken-set",
            "alphabet": ALPHABET,
            "disks": [
                {"position": 1, "sequence": "A"},
                {"position": 2, "sequence": _rotated_sequence(1)},
                {"position": 3, "sequence": _rotated_sequence(2)},
                {"position": 4, "sequence": _rotated_sequence(3)},
            ],
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DISK_SET_VALIDATION_ERROR"


def test_create_rejects_empty_disks_list(db_client, db_session) -> None:
    user = _create_user(db_session, "owner@example.com")

    response = db_client.post(
        "/api/v1/disk-sets",
        json={
            "name": "Empty",
            "slug": "empty-set",
            "alphabet": ALPHABET,
            "disks": [],
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DISK_SET_VALIDATION_ERROR"


def test_patch_rejects_partial_disks_list(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"disks": [{"position": 1, "sequence": ALPHABET}]},
        headers=_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DISK_SET_VALIDATION_ERROR"


def test_create_rejects_owner_id_field(db_client, db_session) -> None:
    user = _create_user(db_session, "owner@example.com")

    response = db_client.post(
        "/api/v1/disk-sets",
        json={
            "name": "Owned Set",
            "slug": "owned-set",
            "alphabet": ALPHABET,
            "disks": _disk_list([0, 1, 2, 3]),
            "owner_id": 999,
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 422
    assert (
        db_session.scalar(select(DiskSetModel).where(DiskSetModel.slug == "owned-set"))
        is None
    )


def test_patch_rejects_owner_id_field(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"owner_id": 999},
        headers=_auth_headers(user),
    )

    assert response.status_code == 422


def test_patch_own_disk_set_does_not_change_owner_id_in_db(
    db_session, db_client
) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    # We send a PATCH that is valid otherwise
    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={"name": "New Name"},
        headers=_auth_headers(user),
    )
    assert response.status_code == 200

    disk_set = _owned_disk_set_model(db_session, created["id"])
    assert disk_set.owner_id == user.id


def test_patch_rejects_empty_payload(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.patch(
        f"/api/v1/disk-sets/{created['id']}",
        json={},
        headers=_auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DISK_SET_VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "Empty update payload"


def test_delete_openapi_shows_204(db_client) -> None:
    response = db_client.get("/openapi.json")

    assert response.status_code == 200
    delete_operation = response.json()["paths"]["/api/v1/disk-sets/{disk_set_id}"][
        "delete"
    ]
    assert "204" in delete_operation["responses"]


def test_existing_stateless_cipher_still_works(client) -> None:
    response = client.post(
        "/api/v1/cipher/encrypt",
        json={
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
            "key": {
                "disk_order": [1, 2, 3, 4],
                "offset": 2,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"


def test_cipher_from_own_created_private_disk_set_works(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json={
            "text": "HELLOWORLD",
            "disk_set_id": created["id"],
            "key": {
                "disk_order": [1, 2, 3, 4],
                "offset": 2,
            },
            "include_trace": True,
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["text"] == "JGNNQYQTNF"


def test_cipher_from_deleted_disk_set_returns_404(db_session, db_client) -> None:
    user = _create_user(db_session, "owner@example.com")
    created = _create_disk_set(db_client, user).json()

    delete_response = db_client.delete(
        f"/api/v1/disk-sets/{created['id']}",
        headers=_auth_headers(user),
    )
    assert delete_response.status_code == 204

    response = db_client.post(
        "/api/v1/cipher/encrypt/from-disk-set",
        json={
            "text": "HELLOWORLD",
            "disk_set_id": created["id"],
            "key": {
                "disk_order": [1, 2, 3, 4],
                "offset": 2,
            },
            "include_trace": True,
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DISK_SET_NOT_FOUND"
