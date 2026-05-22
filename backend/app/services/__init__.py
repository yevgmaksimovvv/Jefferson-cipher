"""Service package."""

from app.services.auth import (
    DuplicateEmailError,
    InvalidCredentialsError,
    authenticate_user,
    create_user_access_token,
    normalize_email,
    register_user,
)

__all__ = [
    "DuplicateEmailError",
    "InvalidCredentialsError",
    "authenticate_user",
    "create_user_access_token",
    "normalize_email",
    "register_user",
]
