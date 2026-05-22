from __future__ import annotations

from app.db.models import DiskModel, DiskSetModel, UserModel
from sqlalchemy import inspect, select


def _disk_set(slug: str, owner_id: int | None = None) -> DiskSetModel:
    return DiskSetModel(
        name=slug.replace("-", " ").title(),
        slug=slug,
        owner_id=owner_id,
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
        ],
    )


def test_public_disk_set_owner_id_can_be_none(db_session) -> None:
    disk_set = _disk_set("public-set")

    db_session.add(disk_set)
    db_session.commit()
    db_session.expunge_all()

    loaded_disk_set = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == "public-set")
    )

    assert loaded_disk_set is not None
    assert loaded_disk_set.owner_id is None


def test_private_disk_set_can_reference_existing_user(db_session) -> None:
    user = UserModel(
        email="owner@example.com",
        hashed_password="hashed-password",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    disk_set = _disk_set("private-set", owner_id=user.id)
    db_session.add(disk_set)
    db_session.commit()
    db_session.expunge_all()

    loaded_disk_set = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == "private-set")
    )

    assert loaded_disk_set is not None
    assert loaded_disk_set.owner_id == user.id


def test_disk_set_owner_column_is_nullable_and_indexed(db_session) -> None:
    mapper = inspect(DiskSetModel)
    assert mapper.columns.owner_id.nullable is True

    inspector = inspect(db_session.get_bind())
    indexes = inspector.get_indexes("disk_sets")
    assert any(index["name"] == "ix_disk_sets_owner_id" for index in indexes)


def test_disk_set_owner_foreign_key_is_non_cascading() -> None:
    foreign_key = next(iter(DiskSetModel.__table__.c.owner_id.foreign_keys))

    assert foreign_key.ondelete is None
