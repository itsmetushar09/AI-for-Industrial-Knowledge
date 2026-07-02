"""Top-level API router composition."""

from fastapi import APIRouter, Depends

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.core.auth import get_current_user
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.ui_support import router as ui_support_router

api_router = APIRouter(dependencies=[Depends(get_current_user)])
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(analytics_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(upload_router)
api_router.include_router(ui_support_router)
