from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import (
    DuplicateEmailError,
    authenticate_user,
    create_user_access_token,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse | JSONResponse:
    try:
        user = register_user(db, payload.email, payload.password)
    except DuplicateEmailError:
        return _error_response(
            "EMAIL_ALREADY_REGISTERED",
            "Email already registered",
            status.HTTP_409_CONFLICT,
        )
    return UserResponse(id=user.id, email=user.email, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse | JSONResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_user_access_token(user))
