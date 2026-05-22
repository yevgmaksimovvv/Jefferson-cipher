from __future__ import annotations

import re
from datetime import datetime, timedelta

import pytest
from app.core.security import generate_refresh_token, hash_refresh_token
from app.repositories.refresh_tokens import (
    create_refresh_token,
    revoke_refresh_token,
)
from app.services.auth import register_user
from sqlalchemy.exc import IntegrityError


def test_refresh_token_row_uses_hash_and_relationship(db_session) -> None:
    user = register_user(db_session, "refresh@example.com", "password123")
    plain_refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(plain_refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)

    refresh_token = create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db_session.commit()
    db_session.refresh(refresh_token)

    assert refresh_token.user_id == user.id
    assert refresh_token.user.email == "refresh@example.com"
    assert refresh_token.token_hash == token_hash
    assert refresh_token.token_hash != plain_refresh_token
    assert re.fullmatch(r"[0-9a-f]{64}", refresh_token.token_hash)
    assert refresh_token.expires_at == expires_at
    assert refresh_token.revoked_at is None
    assert refresh_token.replaced_by_token_id is None


def test_refresh_token_token_hash_is_unique(db_session) -> None:
    user = register_user(db_session, "unique@example.com", "password123")
    token_hash = hash_refresh_token(generate_refresh_token())

    create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_refresh_token(
            db_session,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

    db_session.rollback()


def test_refresh_token_revocation_and_rotation_link(db_session) -> None:
    user = register_user(db_session, "rotation@example.com", "password123")
    first_plain_token = generate_refresh_token()
    first_token = create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=hash_refresh_token(first_plain_token),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    second_plain_token = generate_refresh_token()
    second_token = create_refresh_token(
        db_session,
        user_id=user.id,
        token_hash=hash_refresh_token(second_plain_token),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.commit()

    revoke_refresh_token(
        db_session,
        first_token,
        replaced_by_token_id=second_token.id,
    )
    db_session.commit()
    db_session.refresh(first_token)

    assert first_token.revoked_at is not None
    assert first_token.replaced_by_token_id == second_token.id
