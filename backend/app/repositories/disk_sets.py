from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DiskSetModel


def list_disk_sets(db: Session) -> list[DiskSetModel]:
    return list_accessible_disk_sets(db, user_id=None)


def list_accessible_disk_sets(
    db: Session,
    user_id: int | None,
) -> list[DiskSetModel]:
    stmt = select(DiskSetModel).options(selectinload(DiskSetModel.disks))
    if user_id is None:
        stmt = stmt.where(DiskSetModel.owner_id.is_(None))
    else:
        stmt = stmt.where(
            or_(
                DiskSetModel.owner_id.is_(None),
                DiskSetModel.owner_id == user_id,
            )
        )
    stmt = stmt.order_by(DiskSetModel.id)
    return db.scalars(stmt).all()


def get_accessible_disk_set_by_id(
    db: Session,
    disk_set_id: int,
    user_id: int | None,
) -> DiskSetModel | None:
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.id == disk_set_id)
    )
    if user_id is None:
        stmt = stmt.where(DiskSetModel.owner_id.is_(None))
    else:
        stmt = stmt.where(
            or_(
                DiskSetModel.owner_id.is_(None),
                DiskSetModel.owner_id == user_id,
            )
        )
    return db.scalar(stmt)


def get_disk_set_by_id(db: Session, disk_set_id: int) -> DiskSetModel | None:
    return get_accessible_disk_set_by_id(db, disk_set_id, user_id=None)


def get_disk_set_by_slug(db: Session, slug: str) -> DiskSetModel | None:
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.slug == slug)
    )
    return db.scalar(stmt)
