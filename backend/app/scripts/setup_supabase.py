"""Idempotently enable pgvector and provision the private documents bucket."""

import asyncio
import logging

from asyncpg import InvalidPasswordError
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.supabase import get_supabase_clients
from app.database.session import get_database
from app.storage.service import SupabaseStorageService

logger = logging.getLogger(__name__)


class SetupError(RuntimeError):
    """A sanitized, actionable Supabase provisioning failure."""


async def setup() -> None:
    """Provision only Phase 2 infrastructure; Phase 3 owns application tables."""

    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.supabase_admin_configured:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SECRET_KEY in backend/.env")

    database = get_database()
    if database.engine is None:
        raise RuntimeError("Set DATABASE_URL in backend/.env")

    clients = get_supabase_clients()
    try:
        storage = SupabaseStorageService(clients, settings)
        try:
            await storage.ensure_bucket()
        except Exception as exc:
            raise SetupError(
                "Storage setup failed. Verify SUPABASE_URL and the backend-only "
                "SUPABASE_SECRET_KEY."
            ) from exc

        try:
            async with database.engine.begin() as connection:
                await connection.execute(text("CREATE SCHEMA IF NOT EXISTS extensions"))
                await connection.execute(
                    text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
                )
        except InvalidPasswordError as exc:
            raise SetupError(
                "Database authentication failed. Copy the Session pooler URI from "
                "Supabase Connect and replace [YOUR-PASSWORD] with the project's "
                "database password. Do not use an API key here."
            ) from exc
        logger.info(
            "Supabase Phase 2 setup complete",
            extra={"event": "supabase_setup_complete", "bucket": settings.supabase_storage_bucket},
        )
    finally:
        await clients.close()
        await database.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except ValidationError as exc:
        messages = "; ".join(
            error["msg"] for error in exc.errors(include_input=False, include_url=False)
        )
        raise SystemExit(f"Configuration error: {messages}") from None
    except OperationalError:
        raise SystemExit(
            "Database connection failed. Verify the Session pooler hostname, database "
            "password, and that special password characters are percent-encoded."
        ) from None
    except SetupError as exc:
        raise SystemExit(f"Setup error: {exc}") from None
