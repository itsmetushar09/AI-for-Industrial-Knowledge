"""Analytics dashboard endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import require_roles
from app.models.enums import UserRole
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics import AnalyticsService, get_analytics_service

router = APIRouter(tags=["analytics"])


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get dashboard analytics",
    dependencies=[
        Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.PLANT_MANAGER))
    ],
)
async def analytics(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AnalyticsResponse:
    """Return document, storage, upload, department, and AI usage metrics."""

    return await service.snapshot()
