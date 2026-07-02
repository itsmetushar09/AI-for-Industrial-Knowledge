"""Authenticated profile endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.database.session import Database, get_database
from app.models.profile import Profile
from app.schemas.auth import CurrentUserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
) -> CurrentUserResponse:
    """Return the authoritative application profile for the current JWT."""

    assert database.session_factory is not None
    async with database.session_factory() as session:
        profile = await session.get(Profile, user.id)
        assert profile is not None
        return CurrentUserResponse(
            id=user.id,
            name=profile.full_name,
            email=user.email,
            role=user.role,
            department_id=user.department_id,
        )
