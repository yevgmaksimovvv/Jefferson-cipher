from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth import (
    DuplicateEmailError,
    InvalidRefreshTokenError,
    authenticate_user,
    issue_token_pair,
    logout_refresh_token,
    refresh_token_pair,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _error_response(
    code: str,
    message: str,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
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

    return issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse | JSONResponse:
    try:
        return refresh_token_pair(db, payload.refresh_token)
    except InvalidRefreshTokenError:
        return _error_response(
            "INVALID_REFRESH_TOKEN",
            "Invalid refresh token",
            status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def logout(
    payload: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        logout_refresh_token(db, payload.refresh_token)
    except InvalidRefreshTokenError:
        return _error_response(
            "INVALID_REFRESH_TOKEN",
            "Invalid refresh token",
            status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
