from __future__ import annotations

import logging
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DiskModel, DiskSetModel
from app.db.session import get_session_factory

DEFAULT_DISK_SET_SLUG = "jefferson-standard"
DEFAULT_DISK_SET_NAME = "Jefferson Standard"
DEFAULT_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DEFAULT_DISK_SEQUENCES: tuple[str, ...] = tuple(
    DEFAULT_ALPHABET[index:] + DEFAULT_ALPHABET[:index] for index in range(26)
) + tuple(
    DEFAULT_ALPHABET[::-1][index:] + DEFAULT_ALPHABET[::-1][:index]
    for index in range(10)
)

logger = logging.getLogger(__name__)


def validate_default_disk_sequences() -> None:
    if len(DEFAULT_DISK_SEQUENCES) != 36:
        raise ValueError("DEFAULT_DISK_SEQUENCES must contain exactly 36 sequences")

    expected_letters = set(DEFAULT_ALPHABET)
    if len(DEFAULT_ALPHABET) != 26 or len(expected_letters) != 26:
        raise ValueError("DEFAULT_ALPHABET must contain the letters A-Z exactly once")

    if len(set(DEFAULT_DISK_SEQUENCES)) == 1:
        raise ValueError("DEFAULT_DISK_SEQUENCES must not contain identical sequences")

    for index, sequence in enumerate(DEFAULT_DISK_SEQUENCES, start=1):
        if not isinstance(sequence, str):
            raise ValueError(f"disk sequence #{index} must be a string")
        if len(sequence) != 26:
            raise ValueError(f"disk sequence #{index} must be 26 characters long")
        if set(sequence) != expected_letters:
            raise ValueError(
                f"disk sequence #{index} must contain each letter A-Z exactly once"
            )


def _validate_existing_default_disk_set(disk_set: DiskSetModel) -> None:
    expected_positions = list(range(1, len(DEFAULT_DISK_SEQUENCES) + 1))
    if disk_set.alphabet != DEFAULT_ALPHABET:
        raise ValueError("existing default disk set is invalid: unexpected alphabet")
    if len(disk_set.disks) != len(DEFAULT_DISK_SEQUENCES):
        raise ValueError("existing default disk set is invalid: unexpected disk count")

    positions = [disk.position for disk in disk_set.disks]
    if positions != expected_positions:
        raise ValueError("existing default disk set is invalid: unexpected positions")

    expected_letters = set(DEFAULT_ALPHABET)
    for index, disk in enumerate(disk_set.disks, start=1):
        if not isinstance(disk.sequence, str):
            raise ValueError(f"existing default disk set is invalid: disk #{index}")
        if len(disk.sequence) != len(DEFAULT_ALPHABET):
            raise ValueError(f"existing default disk set is invalid: disk #{index}")
        if set(disk.sequence) != expected_letters:
            raise ValueError(f"existing default disk set is invalid: disk #{index}")


def seed_default_disk_set(db: Session) -> DiskSetModel:
    existing_disk_set = db.scalar(
        select(DiskSetModel).where(DiskSetModel.slug == DEFAULT_DISK_SET_SLUG)
    )
    if existing_disk_set is not None:
        _validate_existing_default_disk_set(existing_disk_set)
        return existing_disk_set

    validate_default_disk_sequences()

    disk_set = DiskSetModel(
        name=DEFAULT_DISK_SET_NAME,
        slug=DEFAULT_DISK_SET_SLUG,
        alphabet=DEFAULT_ALPHABET,
        disks=[
            DiskModel(position=position, sequence=sequence)
            for position, sequence in enumerate(DEFAULT_DISK_SEQUENCES, start=1)
        ],
    )
    db.add(disk_set)
    db.commit()
    db.refresh(disk_set)
    return disk_set


def initialize_database() -> DiskSetModel:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        disk_set = seed_default_disk_set(db)
        _ = len(disk_set.disks)
        return disk_set
    finally:
        db.close()


def main() -> int:
    if not any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, "stream", None) is sys.stdout
        for handler in logger.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    disk_set = initialize_database()
    logger.info(
        "Seeded disk set: "
        f"id={disk_set.id} slug={disk_set.slug} disks={len(disk_set.disks)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
