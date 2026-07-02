"""Supabase client and service behavior tests."""

import httpx
import pytest

from app.core.config import Settings
from app.core.supabase import SupabaseClients


@pytest.mark.asyncio
async def test_supabase_healthcheck_uses_publishable_key() -> None:
    observed_api_key: str | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal observed_api_key
        observed_api_key = request.headers.get("apikey")
        return httpx.Response(200, json={"version": "test"})

    settings = Settings(
        supabase_url="https://project-ref.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        _env_file=None,
    )
    clients = SupabaseClients(settings)
    await clients._http.aclose()
    clients._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        assert await clients.healthcheck() == "connected"
        assert observed_api_key == "sb_publishable_test"
    finally:
        await clients.close()


@pytest.mark.asyncio
async def test_supabase_healthcheck_is_safe_when_unconfigured() -> None:
    clients = SupabaseClients(Settings(_env_file=None))
    try:
        assert await clients.healthcheck() == "not_configured"
        with pytest.raises(RuntimeError, match="publishable key"):
            await clients.public()
    finally:
        await clients.close()
