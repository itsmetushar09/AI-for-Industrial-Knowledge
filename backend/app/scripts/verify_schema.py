"""Verify the deployed Phase 3 schema without exposing credentials or data."""

import asyncio
import json

from sqlalchemy import text

from app.database.session import get_database

EXPECTED_TABLES = {
    "audit_logs",
    "conversations",
    "departments",
    "document_chunks",
    "documents",
    "equipment",
    "knowledge_edges",
    "knowledge_nodes",
    "messages",
    "profiles",
}


async def verify() -> bool:
    """Check revision, tables, RLS, vector extension, and semantic index."""

    database = get_database()
    if database.engine is None:
        raise RuntimeError("DATABASE_URL must be configured")

    try:
        async with database.engine.connect() as connection:
            rows = await connection.execute(
                text(
                    "SELECT tablename, rowsecurity FROM pg_tables "
                    "WHERE schemaname = 'public'"
                )
            )
            table_security = {row.tablename: row.rowsecurity for row in rows}
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            vector_enabled = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            hnsw_index = await connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename = 'document_chunks' "
                    "AND indexname = 'ix_document_chunks_embedding_hnsw')"
                )
            )
    finally:
        await database.dispose()

    missing = sorted(EXPECTED_TABLES - table_security.keys())
    rls_disabled = sorted(
        table for table in EXPECTED_TABLES if table in table_security and not table_security[table]
    )
    result = {
        "revision": revision,
        "tables": len(EXPECTED_TABLES) - len(missing),
        "missing_tables": missing,
        "rls_disabled": rls_disabled,
        "pgvector": bool(vector_enabled),
        "hnsw_index": bool(hnsw_index),
    }
    print(json.dumps(result, indent=2))
    return not missing and not rls_disabled and bool(vector_enabled) and bool(hnsw_index)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(verify()) else 1)

