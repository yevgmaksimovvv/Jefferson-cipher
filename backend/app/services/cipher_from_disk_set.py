from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.cipher.models import CipherKey, CipherResult
from app.domain.cipher.service import decrypt, encrypt
from app.repositories.disk_sets import get_disk_set_by_id
from app.services.disk_sets import disk_set_model_to_domain


def _cipher_with_disk_set_id(
    text: str,
    disk_set_id: int,
    key: CipherKey,
    db: Session,
    transform,
    _include_trace: bool,
) -> CipherResult | None:
    disk_set = get_disk_set_by_id(db, disk_set_id)
    if disk_set is None:
        return None
    domain_disk_set = disk_set_model_to_domain(disk_set)
    return transform(text, domain_disk_set, key)


def encrypt_with_disk_set_id(
    text: str,
    disk_set_id: int,
    key: CipherKey,
    db: Session,
    include_trace: bool = True,
) -> CipherResult | None:
    return _cipher_with_disk_set_id(
        text=text,
        disk_set_id=disk_set_id,
        key=key,
        db=db,
        transform=encrypt,
        _include_trace=include_trace,
    )


def decrypt_with_disk_set_id(
    text: str,
    disk_set_id: int,
    key: CipherKey,
    db: Session,
    include_trace: bool = True,
) -> CipherResult | None:
    return _cipher_with_disk_set_id(
        text=text,
        disk_set_id=disk_set_id,
        key=key,
        db=db,
        transform=decrypt,
        _include_trace=include_trace,
    )
