from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import UserModel
from app.db.session import get_db
from app.repositories.users import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except PyJWTError as exc:
        raise credentials_exception from exc

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise credentials_exception

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise credentials_exception from exc

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user
