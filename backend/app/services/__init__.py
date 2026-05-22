"""Service package."""

from app.services.auth import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    authenticate_user,
    create_user_access_token,
    issue_token_pair,
    logout_refresh_token,
    normalize_email,
    refresh_token_pair,
    register_user,
)

__all__ = [
    "DuplicateEmailError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "authenticate_user",
    "create_user_access_token",
    "issue_token_pair",
    "logout_refresh_token",
    "normalize_email",
    "refresh_token_pair",
    "register_user",
]
