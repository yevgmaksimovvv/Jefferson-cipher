from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.core.audit import log_audit_event
from app.core.rate_limit import rate_limit
from app.db.models import UserModel
from app.db.session import get_db
from app.schemas.cipher import ErrorDetailResponse, ErrorResponse
from app.schemas.disk_set import (
    DiskSetCreateRequest,
    DiskSetListItemResponse,
    DiskSetResponse,
    DiskSetUpdateRequest,
)
from app.services.disk_sets import (
    DiskSetNotFoundError,
    DiskSetSlugAlreadyExistsError,
    DiskSetValidationError,
    create_user_disk_set,
    delete_user_disk_set,
    disk_set_model_to_list_item,
    disk_set_model_to_response,
    get_any_disk_set_by_id,
    get_disk_set_by_id,
    list_disk_sets,
    update_user_disk_set,
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


def _validation_error_response(message: str) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetailResponse(
            code="DISK_SET_VALIDATION_ERROR",
            message=message,
        )
    )
    return JSONResponse(status_code=400, content=payload.model_dump())


def _slug_exists_response() -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetailResponse(
            code="DISK_SET_SLUG_ALREADY_EXISTS",
            message="Disk set slug already exists",
        )
    )
    return JSONResponse(status_code=409, content=payload.model_dump())


@router.get("", response_model=list[DiskSetListItemResponse])
def list_disk_sets_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel | None, Depends(get_optional_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DiskSetListItemResponse]:
    user_id = current_user.id if current_user is not None else None
    return [
        disk_set_model_to_list_item(model)
        for model in list_disk_sets(db, user_id=user_id, limit=limit, offset=offset)
    ]


@router.get("/{disk_set_id}", response_model=DiskSetResponse)
def get_disk_set_endpoint(
    disk_set_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel | None, Depends(get_optional_current_user)],
    request: Request,
) -> DiskSetResponse | JSONResponse:
    user_id = current_user.id if current_user is not None else None
    disk_set = get_disk_set_by_id(db, disk_set_id, user_id=user_id)
    if disk_set is None:
        if current_user is not None:
            existing_disk_set = get_any_disk_set_by_id(db, disk_set_id)
            if (
                existing_disk_set is not None
                and existing_disk_set.owner_id is not None
                and existing_disk_set.owner_id != current_user.id
            ):
                log_audit_event(
                    "disk_set.access.denied",
                    user_id=current_user.id,
                    disk_set_id=disk_set_id,
                    request_id=getattr(request.state, "request_id", None),
                )
        return _disk_set_not_found_response()
    return disk_set_model_to_response(disk_set)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DiskSetResponse,
    dependencies=[Depends(rate_limit("mutation", "RATE_LIMIT_MUTATION_PER_MINUTE"))],
)
def create_disk_set_endpoint(
    payload: DiskSetCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    request: Request,
) -> DiskSetResponse | JSONResponse:
    try:
        disk_set = create_user_disk_set(db, current_user, payload)
    except DiskSetValidationError as error:
        return _validation_error_response(str(error))
    except DiskSetSlugAlreadyExistsError:
        return _slug_exists_response()
    log_audit_event(
        "disk_set.created",
        user_id=current_user.id,
        disk_set_id=disk_set.id,
        request_id=getattr(request.state, "request_id", None),
    )
    return disk_set_model_to_response(disk_set)


@router.patch(
    "/{disk_set_id}",
    response_model=DiskSetResponse,
    dependencies=[Depends(rate_limit("mutation", "RATE_LIMIT_MUTATION_PER_MINUTE"))],
)
def update_disk_set_endpoint(
    disk_set_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    payload: DiskSetUpdateRequest | None = None,
) -> DiskSetResponse | JSONResponse:
    try:
        disk_set = update_user_disk_set(db, disk_set_id, current_user, payload)
    except DiskSetNotFoundError:
        return _disk_set_not_found_response()
    except DiskSetValidationError as error:
        return _validation_error_response(str(error))
    except DiskSetSlugAlreadyExistsError:
        return _slug_exists_response()
    return disk_set_model_to_response(disk_set)


@router.delete(
    "/{disk_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[Depends(rate_limit("mutation", "RATE_LIMIT_MUTATION_PER_MINUTE"))],
)
def delete_disk_set_endpoint(
    disk_set_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> Response | JSONResponse:
    try:
        delete_user_disk_set(db, disk_set_id, current_user)
    except DiskSetNotFoundError:
        return _disk_set_not_found_response()
    except DiskSetValidationError as error:
        return _validation_error_response(str(error))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
