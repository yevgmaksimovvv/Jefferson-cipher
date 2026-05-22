from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DiskSetModel


def list_disk_sets(db: Session) -> list[DiskSetModel]:
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .order_by(DiskSetModel.id)
    )
    return db.scalars(stmt).all()


def get_disk_set_by_id(db: Session, disk_set_id: int) -> DiskSetModel | None:
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.id == disk_set_id)
    )
    return db.scalar(stmt)


def get_disk_set_by_slug(db: Session, slug: str) -> DiskSetModel | None:
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.slug == slug)
    )
    return db.scalar(stmt)
