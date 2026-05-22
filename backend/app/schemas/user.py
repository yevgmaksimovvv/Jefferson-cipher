from __future__ import annotations

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
