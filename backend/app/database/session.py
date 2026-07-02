"""Async SQLAlchemy engine, health checks, and request-scoped sessions."""

import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
DatabaseStatus = Literal["connected", "not_configured", "unavailable"]
ExtensionStatus = Literal["enabled", "disabled", "not_configured", "unavailable"]


def normalize_database_url(url: str) -> str:
    """Convert standard PostgreSQL URLs to SQLAlchemy's asyncpg dialect."""

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Database:
    """Own the async engine and session factory for the process."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

        if settings.database_url is None:
            logger.warning("Database is not configured", extra={"event": "database_unconfigured"})
            return

        database_url = normalize_database_url(settings.database_url.get_secret_value())
        self.engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def healthcheck(self) -> DatabaseStatus:
        """Verify that the configured database accepts a simple query."""

        if self.engine is None:
            return "not_configured"

        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            logger.exception("Database health check failed", extra={"event": "database_health_failed"})
            return "unavailable"
        return "connected"

    async def extension_status(self, extension_name: str) -> ExtensionStatus:
        """Return whether a PostgreSQL extension is available in this database."""

        if self.engine is None:
            return "not_configured"

        try:
            async with self.engine.connect() as connection:
                enabled = await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = :name)"),
                    {"name": extension_name},
                )
        except Exception:
            logger.exception(
                "Database extension check failed",
                extra={"event": "database_extension_check_failed", "extension": extension_name},
            )
            return "unavailable"
        return "enabled" if enabled else "disabled"

    async def dispose(self) -> None:
        """Release all pooled database connections."""

        if self.engine is not None:
            await self.engine.dispose()


@lru_cache
def get_database() -> Database:
    """Return the process-wide database manager."""

    return Database(get_settings())


async def get_db_session(
    database: Database = Depends(get_database),
) -> AsyncIterator[AsyncSession]:
    """Yield a transaction-safe session for a single request."""

    if database.session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )

    async with database.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
