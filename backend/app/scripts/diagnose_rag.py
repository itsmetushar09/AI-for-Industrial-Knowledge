"""Report sanitized RAG readiness without displaying credentials or content."""

import asyncio
import json

from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import get_database


async def diagnose() -> dict[str, object]:
    settings = get_settings()
    database = get_database()
    if database.engine is None:
        raise RuntimeError("DATABASE_URL must be configured")
    try:
        async with database.engine.connect() as connection:
            document_rows = (
                await connection.execute(
                    text(
                        "SELECT status::text AS status, count(*) AS total "
                        "FROM public.documents GROUP BY status ORDER BY status"
                    )
                )
            ).all()
            chunk_rows = (
                await connection.execute(
                    text(
                        "SELECT coalesce(embedding_provider, 'untracked') AS provider, "
                        "coalesce(embedding_model, 'untracked') AS model, count(*) AS total "
                        "FROM public.document_chunks "
                        "GROUP BY embedding_provider, embedding_model ORDER BY 1, 2"
                    )
                )
            ).all()
    finally:
        await database.dispose()

    compatible_chunks = sum(
        row.total
        for row in chunk_rows
        if row.provider == settings.ai_provider and row.model == settings.active_embedding_model
    )
    return {
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_configured,
        "embedding_model": settings.active_embedding_model,
        "documents": {row.status: row.total for row in document_rows},
        "chunk_spaces": [
            {"provider": row.provider, "model": row.model, "chunks": row.total}
            for row in chunk_rows
        ],
        "compatible_chunks": compatible_chunks,
        "rag_ready": settings.ai_configured and compatible_chunks > 0,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(diagnose()), indent=2))

