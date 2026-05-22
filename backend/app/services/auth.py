from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import UserModel
from app.repositories.users import create_user, get_user_by_email


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
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
