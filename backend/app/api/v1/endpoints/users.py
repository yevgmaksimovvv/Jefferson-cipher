from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.models import UserModel
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_endpoint(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
    )
