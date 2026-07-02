"""FastAPI application factory and ASGI entry point."""

import asyncio
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.auth import get_jwt_verifier
from app.core.logging import bind_request_id, configure_logging, reset_request_id
from app.core.gemini import get_gemini_clients
from app.core.openai import get_openai_clients
from app.core.supabase import get_supabase_clients
from app.database.session import get_database
from app.workers.document_processing import recover_queued_documents


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Application started",
            extra={"event": "application_started", "environment": settings.app_env},
        )
        recovery_task: asyncio.Task[None] | None = None
        if settings.database_url is not None and settings.ai_configured:
            recovery_task = asyncio.create_task(
                recover_queued_documents(), name="recover-queued-documents"
            )
        yield
        if recovery_task is not None and not recovery_task.done():
            recovery_task.cancel()
            with suppress(asyncio.CancelledError):
                await recovery_task
        supabase = get_supabase_clients()
        gemini = get_gemini_clients()
        openai = get_openai_clients()
        database = get_database()
        verifier = get_jwt_verifier()
        await openai.close()
        await gemini.close()
        await supabase.close()
        await database.dispose()
        await verifier.close()
        get_supabase_clients.cache_clear()
        get_openai_clients.cache_clear()
        get_gemini_clients.cache_clear()
        get_database.cache_clear()
        get_jwt_verifier.cache_clear()
        logger.info("Application stopped", extra={"event": "application_stopped"})

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.get("/health/live", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        """Unauthenticated process liveness for container orchestrators."""

        return {"status": "alive"}

    @application.middleware("http")
    async def request_logging(request: Request, call_next):
        """Correlate, time, and safely log every HTTP request."""

        supplied_id = request.headers.get("x-request-id", "")
        request_id = (
            supplied_id
            if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_id)
            else str(uuid.uuid4())
        )
        context_token = bind_request_id(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log = logger.error if response.status_code >= 500 else logger.info
            log(
                "HTTP request completed",
                extra={
                    "event": "http_request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception(
                "Unhandled HTTP request failure",
                extra={
                    "event": "http_request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            reset_request_id(context_token)

    application.include_router(api_router)
    return application


app = create_app()
