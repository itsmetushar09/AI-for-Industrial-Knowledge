"""Application health endpoints."""

import asyncio

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.supabase import SupabaseClients, get_supabase_clients
from app.database.session import Database, get_database
from app.storage.service import SupabaseStorageService

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health information returned to infrastructure and operators."""

    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    database: Literal["connected", "not_configured", "unavailable"]
    supabase: Literal["connected", "not_configured", "unavailable"]
    storage: Literal["ready", "missing", "not_configured", "unavailable"]
    pgvector: Literal["enabled", "disabled", "not_configured", "unavailable"]


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
    database: Annotated[Database, Depends(get_database)],
    supabase: Annotated[SupabaseClients, Depends(get_supabase_clients)],
) -> HealthResponse:
    """Return liveness information and the current database connection state."""

    database_status, supabase_status, storage_status, pgvector_status = await asyncio.gather(
        database.healthcheck(),
        supabase.healthcheck(),
        SupabaseStorageService(supabase, settings).healthcheck(),
        database.extension_status("vector"),
    )
    degraded = (
        database_status == "unavailable"
        or supabase_status == "unavailable"
        or storage_status in {"missing", "unavailable"}
        or pgvector_status in {"disabled", "unavailable"}
    )
    return HealthResponse(
        status="degraded" if degraded else "ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database=database_status,
        supabase=supabase_status,
        storage=storage_status,
        pgvector=pgvector_status,
    )
