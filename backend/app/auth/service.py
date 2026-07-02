"""Async Supabase Auth operations used by future HTTP endpoints."""

from typing import Annotated

from fastapi import Depends
from supabase_auth.types import AuthResponse

from app.core.supabase import SupabaseClients, get_supabase_clients


class SupabaseAuthService:
    """Provide low-privilege user authentication through Supabase Auth."""

    def __init__(self, clients: SupabaseClients) -> None:
        self.clients = clients

    async def sign_up(self, email: str, password: str) -> AuthResponse:
        """Create a user using Supabase's configured email confirmation rules."""

        client = await self.clients.public()
        return await client.auth.sign_up({"email": email, "password": password})

    async def sign_in(self, email: str, password: str) -> AuthResponse:
        """Authenticate a user with email and password."""

        client = await self.clients.public()
        return await client.auth.sign_in_with_password({"email": email, "password": password})


def get_auth_service(
    clients: Annotated[SupabaseClients, Depends(get_supabase_clients)],
) -> SupabaseAuthService:
    """Inject the Supabase Auth service into request handlers."""

    return SupabaseAuthService(clients)

