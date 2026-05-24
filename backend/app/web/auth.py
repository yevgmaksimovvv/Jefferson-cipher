from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models import UserModel
from app.repositories.users import get_user_by_id
from app.schemas.auth import TokenResponse
from app.services.auth import InvalidRefreshTokenError, refresh_token_pair


@dataclass(slots=True)
class WebSessionState:
    user: UserModel | None
    refreshed_tokens: TokenResponse | None = None
    clear_cookies: bool = False


def _get_user_from_access_token(token: str, db: Session) -> UserModel | None:
    try:
        payload = decode_access_token(token)
    except PyJWTError:
        return None

    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None

    try:
        user_id = int(subject)
    except ValueError:
        return None

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def resolve_web_session(request: Request, db: Session) -> WebSessionState:
    settings = get_settings()
    access_token = request.cookies.get(settings.WEB_ACCESS_COOKIE_NAME)
    refresh_token = request.cookies.get(settings.WEB_REFRESH_COOKIE_NAME)

    if access_token:
        user = _get_user_from_access_token(access_token, db)
        if user is not None:
            return WebSessionState(user=user)

    if refresh_token:
        try:
            refreshed_tokens = refresh_token_pair(db, refresh_token)
        except InvalidRefreshTokenError:
            return WebSessionState(user=None, clear_cookies=True)

        user = _get_user_from_access_token(refreshed_tokens.access_token, db)
        if user is not None:
            return WebSessionState(user=user, refreshed_tokens=refreshed_tokens)

    if access_token or refresh_token:
        return WebSessionState(user=None, clear_cookies=True)

    return WebSessionState(user=None)


def set_web_session_cookies(response: Response, tokens: TokenResponse) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.WEB_ACCESS_COOKIE_NAME,
        value=tokens.access_token,
        httponly=True,
        secure=settings.WEB_COOKIE_SECURE,
        samesite=settings.WEB_COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.WEB_REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.WEB_COOKIE_SECURE,
        samesite=settings.WEB_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_web_session_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.WEB_ACCESS_COOKIE_NAME,
        path="/",
        secure=settings.WEB_COOKIE_SECURE,
        httponly=True,
        samesite=settings.WEB_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.WEB_REFRESH_COOKIE_NAME,
        path="/",
        secure=settings.WEB_COOKIE_SECURE,
        httponly=True,
        samesite=settings.WEB_COOKIE_SAMESITE,
    )


def resolve_web_csrf_token(request: Request) -> str:
    cached_token = getattr(request.state, "web_csrf_token", None)
    if isinstance(cached_token, str) and cached_token:
        return cached_token

    settings = get_settings()
    csrf_token = request.cookies.get(settings.WEB_CSRF_COOKIE_NAME)
    if not isinstance(csrf_token, str) or not csrf_token:
        csrf_token = secrets.token_urlsafe(32)

    request.state.web_csrf_token = csrf_token
    return csrf_token


def validate_web_csrf_token(request: Request, submitted_token: str | None) -> bool:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.WEB_CSRF_COOKIE_NAME)
    if not isinstance(cookie_token, str) or not cookie_token:
        return False
    if not isinstance(submitted_token, str) or not submitted_token:
        return False
    return secrets.compare_digest(cookie_token, submitted_token)


def set_web_csrf_cookie(response: Response, csrf_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.WEB_CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.WEB_COOKIE_SECURE,
        samesite=settings.WEB_COOKIE_SAMESITE,
        path="/",
    )
