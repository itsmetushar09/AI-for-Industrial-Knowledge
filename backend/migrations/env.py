"""Alembic runtime configured for the async SQLAlchemy engine."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database.session import normalize_database_url
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Get the migration URL exclusively from runtime configuration."""

    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL must be configured before running Alembic")
    return normalize_database_url(settings.database_url.get_secret_value())


def include_object(object_: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    """Exclude Supabase-owned schemas from application migrations."""

    if type_ == "table" and getattr(object_, "info", {}).get("external"):
        return False
    if reflected and getattr(object_, "schema", None) in {"auth", "storage", "extensions"}:
        return False
    return True


def run_migrations_offline() -> None:
    """Render SQL without opening a database connection."""

    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on an established synchronous bridge connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and execute migrations through Alembic's sync bridge."""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())

