from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshTokenModel, UserModel
from app.repositories.refresh_tokens import (
    create_refresh_token,
    get_refresh_token_by_hash,
    revoke_refresh_token,
)
from app.repositories.users import create_user, get_user_by_email, get_user_by_id
from app.schemas.auth import TokenResponse


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, email: str, password: str) -> UserModel:
    normalized_email = normalize_email(email)
    if get_user_by_email(db, normalized_email) is not None:
        raise DuplicateEmailError

    try:
        user = create_user(
            db,
            normalized_email,
            hash_password(password),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError from exc

    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> UserModel | None:
    normalized_email = normalize_email(email)
    user = get_user_by_email(db, normalized_email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user_access_token(user: UserModel) -> str:
    return create_access_token(subject=str(user.id))


def _create_refresh_token_row(
    db: Session,
    user_id: int,
    refresh_token: str,
) -> RefreshTokenModel:
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_refresh_token(
        db,
        user_id=user_id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=expires_at,
    )


def issue_token_pair(db: Session, user: UserModel) -> TokenResponse:
    refresh_token = generate_refresh_token()
    _create_refresh_token_row(db, user.id, refresh_token)
    db.commit()
    return TokenResponse(
        access_token=create_user_access_token(user),
        refresh_token=refresh_token,
    )


def refresh_token_pair(db: Session, refresh_token: str) -> TokenResponse:
    token_hash = hash_refresh_token(refresh_token)
    stored_refresh_token = get_refresh_token_by_hash(db, token_hash)
    if stored_refresh_token is None:
        raise InvalidRefreshTokenError

    if (
        stored_refresh_token.revoked_at is not None
        or stored_refresh_token.expires_at <= datetime.utcnow()
    ):
        raise InvalidRefreshTokenError

    user = get_user_by_id(db, stored_refresh_token.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError

    new_refresh_token = generate_refresh_token()
    new_refresh_token_row = _create_refresh_token_row(db, user.id, new_refresh_token)
    revoke_refresh_token(
        db,
        stored_refresh_token,
        replaced_by_token_id=new_refresh_token_row.id,
    )
    db.commit()
    return TokenResponse(
        access_token=create_user_access_token(user),
        refresh_token=new_refresh_token,
    )


def logout_refresh_token(db: Session, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    stored_refresh_token = get_refresh_token_by_hash(db, token_hash)
    if (
        stored_refresh_token is None
        or stored_refresh_token.revoked_at is not None
        or stored_refresh_token.expires_at <= datetime.utcnow()
    ):
        raise InvalidRefreshTokenError

    revoke_refresh_token(db, stored_refresh_token)
    db.commit()
