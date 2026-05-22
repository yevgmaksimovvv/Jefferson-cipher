from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import DiskSetModel, UserModel
from app.domain.cipher.exceptions import CipherDomainError
from app.domain.cipher.models import Disk, DiskSet
from app.domain.cipher.validators import validate_disk_set
from app.repositories.disk_sets import (
    create_owned_disk_set,
    delete_owned_disk_set,
    get_accessible_disk_set_by_id,
    get_owned_private_disk_set_by_id,
    list_accessible_disk_sets,
    slug_exists,
    update_owned_disk_set,
)
from app.schemas.disk_set import (
    DiskResponse,
    DiskSetCreateRequest,
    DiskSetDiskRequest,
    DiskSetListItemResponse,
    DiskSetResponse,
    DiskSetUpdateRequest,
)


class DiskSetNotFoundError(Exception):
    pass


class DiskSetValidationError(Exception):
    pass


class DiskSetSlugAlreadyExistsError(Exception):
    pass


def _ordered_disks(model: DiskSetModel):
    return sorted(model.disks, key=lambda disk: disk.position)


def list_disk_sets(db: Session, user_id: int | None) -> list[DiskSetModel]:
    return list_accessible_disk_sets(db, user_id=user_id)


def get_disk_set_by_id(
    db: Session,
    disk_set_id: int,
    user_id: int | None,
) -> DiskSetModel | None:
    return get_accessible_disk_set_by_id(db, disk_set_id, user_id=user_id)


def disk_set_model_to_domain(model: DiskSetModel) -> DiskSet:
    disks = tuple(
        Disk(id=disk.position, sequence=disk.sequence) for disk in _ordered_disks(model)
    )
    return DiskSet(disks=disks, alphabet=model.alphabet)


def disk_set_model_to_response(model: DiskSetModel) -> DiskSetResponse:
    return DiskSetResponse(
        id=model.id,
        name=model.name,
        slug=model.slug,
        alphabet=model.alphabet,
        disks=[
            DiskResponse(id=disk.id, position=disk.position, sequence=disk.sequence)
            for disk in _ordered_disks(model)
        ],
    )


def disk_set_model_to_list_item(model: DiskSetModel) -> DiskSetListItemResponse:
    return DiskSetListItemResponse(
        id=model.id,
        name=model.name,
        slug=model.slug,
        alphabet=model.alphabet,
        disks_count=len(model.disks),
    )


def _to_domain_disks(disks: list[DiskSetDiskRequest]) -> tuple[Disk, ...]:
    return tuple(Disk(id=disk.position, sequence=disk.sequence) for disk in disks)


def _validate_disk_set_payload(
    alphabet: str,
    disks: list[DiskSetDiskRequest] | None,
    *,
    existing_disks: list[DiskSetDiskRequest] | None = None,
) -> None:
    candidate_disks = disks if disks is not None else existing_disks
    if candidate_disks is None or not candidate_disks:
        raise DiskSetValidationError("Empty update payload")
    domain_disk_set = DiskSet(
        alphabet=alphabet,
        disks=_to_domain_disks(candidate_disks),
    )
    try:
        validate_disk_set(domain_disk_set)
    except CipherDomainError as exc:
        raise DiskSetValidationError(str(exc) or exc.__class__.__name__) from exc


def create_user_disk_set(
    db: Session,
    current_user: UserModel,
    payload: DiskSetCreateRequest,
) -> DiskSetModel:
    if not payload.disks:
        raise DiskSetValidationError("Disks list cannot be empty")
    _validate_disk_set_payload(payload.alphabet, payload.disks)
    if slug_exists(db, payload.slug):
        raise DiskSetSlugAlreadyExistsError

    try:
        disk_set = create_owned_disk_set(
            db,
            owner_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
            alphabet=payload.alphabet,
            disks=payload.disks,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DiskSetSlugAlreadyExistsError from exc

    db.refresh(disk_set)
    return disk_set


def update_user_disk_set(
    db: Session,
    disk_set_id: int,
    current_user: UserModel,
    payload: DiskSetUpdateRequest | None,
) -> DiskSetModel:
    if payload is None or not payload.model_dump(exclude_none=True):
        raise DiskSetValidationError("Empty update payload")

    disk_set = get_owned_private_disk_set_by_id(db, disk_set_id, current_user.id)
    if disk_set is None:
        raise DiskSetNotFoundError

    alphabet = payload.alphabet if payload.alphabet is not None else disk_set.alphabet
    existing_disks = [
        DiskSetDiskRequest(position=disk.position, sequence=disk.sequence)
        for disk in disk_set.disks
    ]
    if payload.disks is not None and len(payload.disks) != len(existing_disks):
        raise DiskSetValidationError("Full disk list required")
    _validate_disk_set_payload(alphabet, payload.disks, existing_disks=existing_disks)

    slug = payload.slug if payload.slug is not None else disk_set.slug
    if slug_exists(db, slug, exclude_disk_set_id=disk_set_id):
        raise DiskSetSlugAlreadyExistsError

    try:
        disk_set = update_owned_disk_set(
            db,
            disk_set_id,
            current_user.id,
            name=payload.name,
            slug=payload.slug,
            alphabet=payload.alphabet,
            disks=payload.disks,
        )
        if disk_set is None:
            raise DiskSetNotFoundError
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DiskSetSlugAlreadyExistsError from exc

    db.refresh(disk_set)
    return disk_set


def delete_user_disk_set(
    db: Session,
    disk_set_id: int,
    current_user: UserModel,
) -> None:
    if not delete_owned_disk_set(db, disk_set_id, current_user.id):
        raise DiskSetNotFoundError

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DiskSetValidationError("Failed to delete disk set") from exc
