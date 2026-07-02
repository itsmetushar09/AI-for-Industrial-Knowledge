"""Authenticated user response schemas."""

import uuid

from pydantic import BaseModel

from app.models.enums import UserRole


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    role: UserRole
    department_id: uuid.UUID | None
