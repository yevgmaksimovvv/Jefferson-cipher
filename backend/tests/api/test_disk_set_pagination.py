from __future__ import annotations

from app.core.security import create_access_token
from app.db.models import DiskModel, DiskSetModel, UserModel

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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


def _create_disk_set(db_session, slug: str, owner_id: int) -> DiskSetModel:
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


def test_list_disk_sets_accepts_limit_and_offset(db_session, db_client) -> None:
    user = _create_user(db_session, "pagination@example.com")
    first = _create_disk_set(db_session, "pagination-a", owner_id=user.id)
    second = _create_disk_set(db_session, "pagination-b", owner_id=user.id)
    third = _create_disk_set(db_session, "pagination-c", owner_id=user.id)

    first_page = db_client.get(
        "/api/v1/disk-sets?limit=2&offset=0",
        headers=_auth_headers(user),
    )
    second_page = db_client.get(
        "/api/v1/disk-sets?limit=2&offset=2",
        headers=_auth_headers(user),
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    first_body = first_page.json()
    second_body = second_page.json()

    assert len(first_body) == 2
    assert len(second_body) == 1
    assert {item["id"] for item in first_body}.isdisjoint(
        {item["id"] for item in second_body}
    )
    assert {first.id, second.id, third.id} == {
        item["id"] for item in first_body + second_body
    }


def test_list_disk_sets_rejects_limit_above_max(db_client) -> None:
    response = db_client.get("/api/v1/disk-sets?limit=1000")

    assert response.status_code == 422


def test_list_disk_sets_rejects_negative_offset(db_client) -> None:
    response = db_client.get("/api/v1/disk-sets?offset=-1")

    assert response.status_code == 422
