"""Async Supabase client lifecycle and dependency injection."""

import asyncio
import logging
from functools import lru_cache
from typing import Literal

import httpx
from supabase import AsyncClient, acreate_client
from supabase.lib.client_options import AsyncClientOptions

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
SupabaseStatus = Literal["connected", "not_configured", "unavailable"]


class SupabaseClients:
    """Lazily create public and privileged Supabase SDK clients."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(timeout=settings.supabase_request_timeout)
        self._public: AsyncClient | None = None
        self._admin: AsyncClient | None = None
        self._lock = asyncio.Lock()

    def _options(self) -> AsyncClientOptions:
        return AsyncClientOptions(
            auto_refresh_token=False,
            persist_session=False,
            postgrest_client_timeout=self.settings.supabase_request_timeout,
            storage_client_timeout=self.settings.supabase_request_timeout,
            function_client_timeout=self.settings.supabase_request_timeout,
            httpx_client=self._http,
        )

    async def public(self) -> AsyncClient:
        """Return a low-privilege client for Auth and user-scoped operations."""

        if not self.settings.supabase_public_configured:
            raise RuntimeError("Supabase URL and publishable key are not configured")
        async with self._lock:
            if self._public is None:
                assert self.settings.supabase_url is not None
                assert self.settings.supabase_publishable_key is not None
                self._public = await acreate_client(
                    str(self.settings.supabase_url).rstrip("/"),
                    self.settings.supabase_publishable_key.get_secret_value(),
                    options=self._options(),
                )
        return self._public

    async def admin(self) -> AsyncClient:
        """Return the backend-only client that bypasses Row Level Security."""

        if not self.settings.supabase_admin_configured:
            raise RuntimeError("Supabase URL and secret key are not configured")
        async with self._lock:
            if self._admin is None:
                assert self.settings.supabase_url is not None
                assert self.settings.supabase_secret_key is not None
                self._admin = await acreate_client(
                    str(self.settings.supabase_url).rstrip("/"),
                    self.settings.supabase_secret_key.get_secret_value(),
                    options=self._options(),
                )
        return self._admin

    async def healthcheck(self) -> SupabaseStatus:
        """Check availability of the Supabase Auth gateway."""

        if not self.settings.supabase_public_configured:
            return "not_configured"
        assert self.settings.supabase_url is not None
        assert self.settings.supabase_publishable_key is not None
        try:
            response = await self._http.get(
                f"{str(self.settings.supabase_url).rstrip('/')}/auth/v1/health",
                headers={
                    "apikey": self.settings.supabase_publishable_key.get_secret_value(),
                },
            )
            response.raise_for_status()
        except Exception:
            logger.exception("Supabase health check failed", extra={"event": "supabase_health_failed"})
            return "unavailable"
        return "connected"

    async def close(self) -> None:
        """Close the shared HTTP transport used by all SDK clients."""

        await self._http.aclose()


@lru_cache
def get_supabase_clients() -> SupabaseClients:
    """Return the process-wide Supabase client manager."""

    return SupabaseClients(get_settings())

