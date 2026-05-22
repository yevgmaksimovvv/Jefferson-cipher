from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserModel


def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
    stmt = select(UserModel).where(UserModel.id == user_id)
    return db.scalar(stmt)


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    stmt = select(UserModel).where(UserModel.email == email)
    return db.scalar(stmt)


def create_user(db: Session, email: str, hashed_password: str) -> UserModel:
    user = UserModel(email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    return user
