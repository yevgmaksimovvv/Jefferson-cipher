from __future__ import annotations

import pytest
from app.db.models import UserModel
from app.repositories.users import get_user_by_email
from app.services.auth import normalize_email, register_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def test_can_create_user(db_session) -> None:
    user = UserModel(
        email="alice@example.com",
        hashed_password="hashed-password",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    loaded_user = db_session.scalar(
        select(UserModel).where(UserModel.email == "alice@example.com")
    )

    assert loaded_user is not None
    assert loaded_user.id is not None
    assert loaded_user.email == "alice@example.com"
    assert loaded_user.hashed_password == "hashed-password"
    assert loaded_user.is_active is True
    assert loaded_user.created_at is not None
    assert loaded_user.updated_at is not None


def test_unique_email_constraint(db_session) -> None:
    first_user = UserModel(
        email="duplicate@example.com",
        hashed_password="hashed-password-1",
    )
    second_user = UserModel(
        email="duplicate@example.com",
        hashed_password="hashed-password-2",
    )

    db_session.add(first_user)
    db_session.commit()

    db_session.add(second_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_is_active_defaults_to_true(db_session) -> None:
    user = UserModel(
        email="active@example.com",
        hashed_password="hashed-password",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.is_active is True


def test_created_at_is_populated(db_session) -> None:
    user = UserModel(
        email="timestamp@example.com",
        hashed_password="hashed-password",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.created_at is not None


def test_get_user_by_email_uses_exact_normalized_email(db_session) -> None:
    user = register_user(db_session, "  Alice@Example.com  ", "password123")

    loaded_user = get_user_by_email(db_session, normalize_email("Alice@Example.com"))

    assert loaded_user is not None
    assert loaded_user.id == user.id
    assert loaded_user.email == "alice@example.com"
