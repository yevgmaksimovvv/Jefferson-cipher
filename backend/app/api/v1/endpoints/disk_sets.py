from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.disk_sets import get_disk_set_by_id, list_disk_sets
from app.schemas.cipher import ErrorDetailResponse, ErrorResponse
from app.schemas.disk_set import DiskSetListItemResponse, DiskSetResponse
from app.services.disk_sets import (
    disk_set_model_to_list_item,
    disk_set_model_to_response,
)

router = APIRouter(prefix="/disk-sets", tags=["disk-sets"])


def _disk_set_not_found_response() -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetailResponse(
            code="DISK_SET_NOT_FOUND",
            message="Disk set not found",
        )
    )
    return JSONResponse(status_code=404, content=payload.model_dump())


@router.get("", response_model=list[DiskSetListItemResponse])
def list_disk_sets_endpoint(
    db: Annotated[Session, Depends(get_db)],
) -> list[DiskSetListItemResponse]:
    return [disk_set_model_to_list_item(model) for model in list_disk_sets(db)]


@router.get("/{disk_set_id}", response_model=DiskSetResponse)
def get_disk_set_endpoint(
    disk_set_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> DiskSetResponse | JSONResponse:
    disk_set = get_disk_set_by_id(db, disk_set_id)
    if disk_set is None:
        return _disk_set_not_found_response()
    return disk_set_model_to_response(disk_set)
