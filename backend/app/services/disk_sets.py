from __future__ import annotations

from app.db.models import DiskSetModel
from app.domain.cipher.models import Disk, DiskSet
from app.schemas.disk_set import DiskResponse, DiskSetListItemResponse, DiskSetResponse


def _ordered_disks(model: DiskSetModel):
    return sorted(model.disks, key=lambda disk: disk.position)


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
