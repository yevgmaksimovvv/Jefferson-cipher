import pytest
from app.db.models import DiskModel, DiskSetModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def test_can_create_disk_set_with_two_disks(db_session):
    disk_set = DiskSetModel(
        name="Test Set",
        slug="test-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ],
    )

    db_session.add(disk_set)
    db_session.commit()
    db_session.expunge_all()

    loaded_disk_set = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == "test-set")
    )
    assert loaded_disk_set is not None
    assert len(loaded_disk_set.disks) == 2
    assert [disk.position for disk in loaded_disk_set.disks] == [1, 2]


def test_unique_slug_constraint(db_session):
    first_disk_set = DiskSetModel(
        name="First Set",
        slug="duplicate-slug",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )
    second_disk_set = DiskSetModel(
        name="Second Set",
        slug="duplicate-slug",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )

    db_session.add(first_disk_set)
    db_session.commit()

    db_session.add(second_disk_set)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_position_constraint_per_disk_set(db_session):
    disk_set = DiskSetModel(
        name="Position Set",
        slug="position-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ],
    )
    db_session.add(disk_set)
    db_session.commit()

    disk_set.disks.append(DiskModel(position=1, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_same_position_is_allowed_in_different_disk_sets(db_session):
    first_disk_set = DiskSetModel(
        name="First Set",
        slug="first-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ")],
    )
    second_disk_set = DiskSetModel(
        name="Second Set",
        slug="second-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[DiskModel(position=1, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA")],
    )

    db_session.add_all([first_disk_set, second_disk_set])
    db_session.commit()

    assert first_disk_set.id is not None
    assert second_disk_set.id is not None


def test_cascade_delete_removes_disks(db_session):
    disk_set = DiskSetModel(
        name="Cascade Set",
        slug="cascade-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
        ],
    )

    db_session.add(disk_set)
    db_session.commit()
    disk_set_id = disk_set.id
    assert disk_set_id is not None

    db_session.delete(disk_set)
    db_session.commit()

    assert db_session.get(DiskSetModel, disk_set_id) is None
    assert db_session.query(DiskModel).count() == 0


def test_relationship_orders_disks_by_position(db_session):
    disk_set = DiskSetModel(
        name="Ordered Set",
        slug="ordered-set",
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        disks=[
            DiskModel(position=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            DiskModel(position=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
        ],
    )

    db_session.add(disk_set)
    db_session.commit()
    db_session.expunge_all()

    loaded_disk_set = db_session.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == "ordered-set")
    )

    assert loaded_disk_set is not None
    assert [disk.position for disk in loaded_disk_set.disks] == [1, 2, 3]
