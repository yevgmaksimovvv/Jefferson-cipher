from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.core.rate_limit import rate_limit
from app.db.models import UserModel
from app.db.session import get_db
from app.domain.cipher.exceptions import CipherDomainError
from app.domain.cipher.models import CipherKey, CipherResult, Disk, DiskSet
from app.domain.cipher.service import decrypt, encrypt
from app.schemas.cipher import (
    CipherByDiskSetRequest,
    CipherRequest,
    CipherResponse,
    CipherStepResponse,
    ErrorDetailResponse,
    ErrorResponse,
)
from app.services.cipher_from_disk_set import (
    decrypt_with_disk_set_id,
    encrypt_with_disk_set_id,
)

router = APIRouter(prefix="/cipher", tags=["cipher"])


def _to_disk_set(payload: CipherRequest) -> DiskSet:
    return DiskSet(
        alphabet=payload.disk_set.alphabet,
        disks=tuple(
            Disk(id=disk.id, sequence=disk.sequence) for disk in payload.disk_set.disks
        ),
    )


def _to_key(payload: CipherRequest) -> CipherKey:
    return CipherKey(
        disk_order=tuple(payload.key.disk_order),
        offset=payload.key.offset,
    )


def _to_response(result: CipherResult, include_trace: bool) -> CipherResponse:
    trace = []
    if include_trace:
        trace = [
            CipherStepResponse(
                block_index=step.block_index,
                char_index=step.char_index,
                disk_id=step.disk_id,
                input_char=step.input_char,
                output_char=step.output_char,
                input_position=step.input_position,
                output_position=step.output_position,
                offset=step.offset,
                mode=step.mode,
            )
            for step in result.trace
        ]

    return CipherResponse(
        text=result.text,
        normalized_text=result.normalized_text,
        trace=trace,
    )


def _domain_error_response(error: CipherDomainError) -> JSONResponse:
    message = str(error) or error.__class__.__name__
    payload = ErrorResponse(
        error=ErrorDetailResponse(
            code=error.__class__.__name__,
            message=message,
        )
    )
    return JSONResponse(status_code=400, content=payload.model_dump())


def _disk_set_not_found_response() -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetailResponse(
            code="DISK_SET_NOT_FOUND",
            message="Disk set not found",
        )
    )
    return JSONResponse(status_code=404, content=payload.model_dump())


@router.post(
    "/encrypt",
    response_model=CipherResponse,
    summary="Encrypt text",
    description="Encrypts text with an inline disk set and key.",
    response_description="Cipher result.",
    responses={
        400: {
            "description": "Cipher validation error.",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
        },
    },
    dependencies=[Depends(rate_limit("cipher", "RATE_LIMIT_CIPHER_PER_MINUTE"))],
)
def encrypt_cipher(payload: CipherRequest) -> CipherResponse | JSONResponse:
    try:
        result = encrypt(payload.text, _to_disk_set(payload), _to_key(payload))
    except CipherDomainError as error:
        return _domain_error_response(error)
    return _to_response(result, payload.include_trace)


@router.post(
    "/decrypt",
    response_model=CipherResponse,
    summary="Decrypt text",
    description="Decrypts text with an inline disk set and key.",
    response_description="Cipher result.",
    responses={
        400: {
            "description": "Cipher validation error.",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
        },
    },
    dependencies=[Depends(rate_limit("cipher", "RATE_LIMIT_CIPHER_PER_MINUTE"))],
)
def decrypt_cipher(payload: CipherRequest) -> CipherResponse | JSONResponse:
    try:
        result = decrypt(payload.text, _to_disk_set(payload), _to_key(payload))
    except CipherDomainError as error:
        return _domain_error_response(error)
    return _to_response(result, payload.include_trace)


@router.post(
    "/encrypt/from-disk-set",
    response_model=CipherResponse,
    summary="Encrypt from disk set",
    description="Encrypts text using a persisted disk set accessible to the caller.",
    response_description="Cipher result.",
    responses={
        400: {
            "description": "Cipher validation error.",
            "model": ErrorResponse,
        },
        401: {
            "description": "Invalid bearer token.",
            "model": ErrorResponse,
        },
        404: {
            "description": "Disk set not found or not accessible.",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
        },
    },
    openapi_extra={"security": []},
    dependencies=[Depends(rate_limit("cipher", "RATE_LIMIT_CIPHER_PER_MINUTE"))],
)
def encrypt_cipher_from_disk_set(
    payload: CipherByDiskSetRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel | None, Depends(get_optional_current_user)],
) -> CipherResponse | JSONResponse:
    try:
        result = encrypt_with_disk_set_id(
            text=payload.text,
            disk_set_id=payload.disk_set_id,
            key=CipherKey(
                disk_order=tuple(payload.key.disk_order),
                offset=payload.key.offset,
            ),
            db=db,
            user_id=current_user.id if current_user is not None else None,
            include_trace=payload.include_trace,
        )
    except CipherDomainError as error:
        return _domain_error_response(error)
    if result is None:
        return _disk_set_not_found_response()
    return _to_response(result, payload.include_trace)


@router.post(
    "/decrypt/from-disk-set",
    response_model=CipherResponse,
    summary="Decrypt from disk set",
    description="Decrypts text using a persisted disk set accessible to the caller.",
    response_description="Cipher result.",
    responses={
        400: {
            "description": "Cipher validation error.",
            "model": ErrorResponse,
        },
        401: {
            "description": "Invalid bearer token.",
            "model": ErrorResponse,
        },
        404: {
            "description": "Disk set not found or not accessible.",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
        },
    },
    openapi_extra={"security": []},
    dependencies=[Depends(rate_limit("cipher", "RATE_LIMIT_CIPHER_PER_MINUTE"))],
)
def decrypt_cipher_from_disk_set(
    payload: CipherByDiskSetRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel | None, Depends(get_optional_current_user)],
) -> CipherResponse | JSONResponse:
    try:
        result = decrypt_with_disk_set_id(
            text=payload.text,
            disk_set_id=payload.disk_set_id,
            key=CipherKey(
                disk_order=tuple(payload.key.disk_order),
                offset=payload.key.offset,
            ),
            db=db,
            user_id=current_user.id if current_user is not None else None,
            include_trace=payload.include_trace,
        )
    except CipherDomainError as error:
        return _domain_error_response(error)
    if result is None:
        return _disk_set_not_found_response()
    return _to_response(result, payload.include_trace)
