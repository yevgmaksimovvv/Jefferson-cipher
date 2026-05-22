from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DiskModel, DiskSetModel
from app.schemas.disk_set import DiskSetDiskRequest


def list_disk_sets(db: Session) -> list[DiskSetModel]:
    """Возвращает список всех публичных наборов дисков."""
    return list_accessible_disk_sets(db, user_id=None)


def list_accessible_disk_sets(
    db: Session,
    user_id: int | None,
    limit: int = 50,
    offset: int = 0,
) -> list[DiskSetModel]:
    """Возвращает список доступных пользователю наборов: публичные и свои."""
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
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


def get_accessible_disk_set_by_id(
    db: Session,
    disk_set_id: int,
    user_id: int | None,
) -> DiskSetModel | None:
    """Возвращает набор дисков по ID, если он доступен пользователю."""
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
    """Возвращает публичный набор дисков по его ID."""
    return get_accessible_disk_set_by_id(db, disk_set_id, user_id=None)


def get_disk_set_by_slug(db: Session, slug: str) -> DiskSetModel | None:
    """Возвращает набор дисков по его слагу (slug)."""
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.slug == slug)
    )
    return db.scalar(stmt)


def get_any_disk_set_by_id(db: Session, disk_set_id: int) -> DiskSetModel | None:
    """Возвращает набор дисков по ID без фильтра видимости."""
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(DiskSetModel.id == disk_set_id)
    )
    return db.scalar(stmt)


def slug_exists(
    db: Session,
    slug: str,
    exclude_disk_set_id: int | None = None,
) -> bool:
    """Проверяет существование слага в базе данных."""
    stmt = select(DiskSetModel.id).where(DiskSetModel.slug == slug)
    if exclude_disk_set_id is not None:
        stmt = stmt.where(DiskSetModel.id != exclude_disk_set_id)
    return db.scalar(stmt.limit(1)) is not None


def create_owned_disk_set(
    db: Session,
    owner_id: int,
    name: str,
    slug: str,
    alphabet: str,
    disks: list[DiskSetDiskRequest],
) -> DiskSetModel:
    """Создаёт новый приватный набор дисков для указанного владельца."""
    disk_set = DiskSetModel(
        name=name,
        slug=slug,
        owner_id=owner_id,
        alphabet=alphabet,
        disks=[
            DiskModel(position=disk.position, sequence=disk.sequence) for disk in disks
        ],
    )
    db.add(disk_set)
    db.flush()
    return disk_set


def get_owned_private_disk_set_by_id(
    db: Session,
    disk_set_id: int,
    owner_id: int,
) -> DiskSetModel | None:
    """Возвращает приватный набор дисков по ID, проверяя владение."""
    stmt = (
        select(DiskSetModel)
        .options(selectinload(DiskSetModel.disks))
        .where(
            DiskSetModel.id == disk_set_id,
            DiskSetModel.owner_id == owner_id,
            DiskSetModel.owner_id.is_not(None),
        )
    )
    return db.scalar(stmt)


def update_owned_disk_set(
    db: Session,
    disk_set_id: int,
    owner_id: int,
    *,
    name: str | None = None,
    slug: str | None = None,
    alphabet: str | None = None,
    disks: list[DiskSetDiskRequest] | None = None,
) -> DiskSetModel | None:
    """Обновляет данные приватного набора дисков."""
    disk_set = get_owned_private_disk_set_by_id(db, disk_set_id, owner_id)
    if disk_set is None:
        return None

    if name is not None:
        disk_set.name = name
    if slug is not None:
        disk_set.slug = slug
    if alphabet is not None:
        disk_set.alphabet = alphabet
    if disks is not None:
        disk_set.disks.clear()
        db.flush()
        disk_set.disks = [
            DiskModel(position=disk.position, sequence=disk.sequence) for disk in disks
        ]

    db.flush()
    return disk_set


def delete_owned_disk_set(
    db: Session,
    disk_set_id: int,
    owner_id: int,
) -> bool:
    """Удаляет приватный набор дисков."""
    disk_set = get_owned_private_disk_set_by_id(db, disk_set_id, owner_id)
    if disk_set is None:
        return False

    db.delete(disk_set)
    db.flush()
    return True
