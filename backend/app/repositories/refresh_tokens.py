from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RefreshTokenModel


def create_refresh_token(
    db: Session,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> RefreshTokenModel:
    """Сохраняет новый хеш refresh-токена в базе данных."""
    refresh_token = RefreshTokenModel(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.flush()
    return refresh_token


def get_refresh_token_by_hash(
    db: Session,
    token_hash: str,
) -> RefreshTokenModel | None:
    """Ищет запись о refresh-токене по его хешу."""
    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
    return db.scalar(stmt)


def revoke_refresh_token(
    db: Session,
    refresh_token: RefreshTokenModel,
    replaced_by_token_id: int | None = None,
) -> RefreshTokenModel:
    """Отзывает refresh-токен, помечая его как использованный/аннулированный."""
    if refresh_token.revoked_at is None:
        refresh_token.revoked_at = datetime.utcnow()
    refresh_token.replaced_by_token_id = replaced_by_token_id
    db.flush()
    return refresh_token
