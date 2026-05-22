from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.rate_limit import rate_limit
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
    dependencies=[Depends(rate_limit("auth", "RATE_LIMIT_AUTH_PER_MINUTE"))],
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


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth", "RATE_LIMIT_AUTH_PER_MINUTE"))],
)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    request: Request,
) -> TokenResponse | JSONResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        log_audit_event(
            "auth.login.failure",
            email=payload.email.lower(),
            request_id=getattr(request.state, "request_id", None),
        )
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

    log_audit_event(
        "auth.login.success",
        user_id=user.id,
        email=user.email,
        request_id=getattr(request.state, "request_id", None),
    )
    return issue_token_pair(db, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("refresh", "RATE_LIMIT_REFRESH_PER_MINUTE"))],
)
def refresh(
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
    request: Request,
) -> TokenResponse | JSONResponse:
    try:
        return refresh_token_pair(
            db,
            payload.refresh_token,
            request_id=getattr(request.state, "request_id", None),
        )
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
    dependencies=[Depends(rate_limit("auth", "RATE_LIMIT_AUTH_PER_MINUTE"))],
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
