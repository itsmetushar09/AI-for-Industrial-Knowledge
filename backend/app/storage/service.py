"""Supabase Storage implementation for private industrial documents."""

from typing import Annotated, Literal

from fastapi import Depends
from storage3.exceptions import StorageApiError

from app.core.config import Settings, get_settings
from app.core.supabase import SupabaseClients, get_supabase_clients

StorageStatus = Literal["ready", "missing", "not_configured", "unavailable"]


class SupabaseStorageService:
    """Read and write objects in the configured private documents bucket."""

    def __init__(self, clients: SupabaseClients, settings: Settings) -> None:
        self.clients = clients
        self.settings = settings

    async def healthcheck(self) -> StorageStatus:
        """Check access to the configured bucket without mutating it."""

        if not self.settings.supabase_admin_configured:
            return "not_configured"
        try:
            client = await self.clients.admin()
            await client.storage.get_bucket(self.settings.supabase_storage_bucket)
        except StorageApiError as exc:
            return "missing" if str(exc.status) == "404" else "unavailable"
        except Exception:
            return "unavailable"
        return "ready"

    async def ensure_bucket(self) -> None:
        """Create the private PDF bucket when it does not already exist."""

        client = await self.clients.admin()
        try:
            await client.storage.get_bucket(self.settings.supabase_storage_bucket)
            return
        except StorageApiError as exc:
            if str(exc.status) != "404":
                raise

        await client.storage.create_bucket(
            self.settings.supabase_storage_bucket,
            options={
                "public": False,
                "file_size_limit": self.settings.supabase_storage_max_file_size,
                "allowed_mime_types": ["application/pdf"],
            },
        )

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Upload a new private object and return its bucket-relative path."""

        client = await self.clients.admin()
        await client.storage.from_(self.settings.supabase_storage_bucket).upload(
            path=path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
        return path

    async def download(self, path: str) -> bytes:
        """Download a private object."""

        client = await self.clients.admin()
        return await client.storage.from_(self.settings.supabase_storage_bucket).download(path)

    async def delete(self, path: str) -> None:
        """Delete a private object."""

        client = await self.clients.admin()
        await client.storage.from_(self.settings.supabase_storage_bucket).remove([path])


def get_storage_service(
    clients: Annotated[SupabaseClients, Depends(get_supabase_clients)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupabaseStorageService:
    """Inject the configured object storage service."""

    return SupabaseStorageService(clients, settings)

