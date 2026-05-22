import pytest
from app.db.init_db import (
    DEFAULT_ALPHABET,
    DEFAULT_DISK_SET_NAME,
    DEFAULT_DISK_SET_SLUG,
    seed_default_disk_set,
    validate_default_disk_sequences,
)
from app.db.models import DiskModel, DiskSetModel
from sqlalchemy import select


def test_validate_default_disk_sequences_passes():
    validate_default_disk_sequences()


def test_seed_default_disk_set_creates_expected_rows(db_session):
    disk_set = seed_default_disk_set(db_session)

    assert disk_set.slug == DEFAULT_DISK_SET_SLUG
    assert disk_set.name == DEFAULT_DISK_SET_NAME
    assert len(disk_set.disks) == 36
    assert [disk.position for disk in disk_set.disks] == list(range(1, 37))
    assert all(len(disk.sequence) == 26 for disk in disk_set.disks)
    assert all(set(disk.sequence) == set(DEFAULT_ALPHABET) for disk in disk_set.disks)
    assert len({disk.sequence for disk in disk_set.disks}) > 1


def test_seed_default_disk_set_is_idempotent(db_session):
    first_disk_set = seed_default_disk_set(db_session)
    second_disk_set = seed_default_disk_set(db_session)

    assert second_disk_set.id == first_disk_set.id

    disk_sets = db_session.scalars(select(DiskSetModel)).all()
    assert len(disk_sets) == 1
    assert len(disk_sets[0].disks) == 36
    assert len(db_session.scalars(select(DiskSetModel)).all()) == 1
    assert (
        db_session.scalar(
            select(DiskSetModel).where(DiskSetModel.slug == DEFAULT_DISK_SET_SLUG)
        )
        is not None
    )


@pytest.mark.parametrize(
    "disks, expected_message",
    [
        ([], "existing default disk set is invalid"),
        (
            [DiskModel(position=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ")],
            "existing default disk set is invalid",
        ),
        (
            [
                DiskModel(position=position, sequence="A" * 26)
                for position in range(1, 37)
            ],
            "existing default disk set is invalid",
        ),
    ],
)
def test_seed_default_disk_set_rejects_corrupted_existing_seed(
    db_session,
    disks,
    expected_message,
):
    disk_set = DiskSetModel(
        name=DEFAULT_DISK_SET_NAME,
        slug=DEFAULT_DISK_SET_SLUG,
        alphabet=DEFAULT_ALPHABET,
        disks=disks,
    )
    db_session.add(disk_set)
    db_session.commit()

    with pytest.raises(ValueError, match=expected_message):
        seed_default_disk_set(db_session)
