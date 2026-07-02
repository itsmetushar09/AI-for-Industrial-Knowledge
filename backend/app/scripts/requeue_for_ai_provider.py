"""Requeue documents whose vectors belong to another AI provider/model."""

import asyncio
import json

from sqlalchemy import exists, select, update

from app.core.config import get_settings
from app.database.session import get_database
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus


async def requeue() -> dict[str, object]:
    """Mark incompatible indexed/failed documents for safe background reprocessing."""

    settings = get_settings()
    database = get_database()
    if database.session_factory is None:
        raise RuntimeError("DATABASE_URL must be configured")
    if not settings.ai_configured:
        raise RuntimeError(f"Configure {settings.ai_provider.title()} before re-queueing documents")

    compatible_chunk = exists(
        select(DocumentChunk.id).where(
            DocumentChunk.document_id == Document.id,
            DocumentChunk.embedding_provider == settings.ai_provider,
            DocumentChunk.embedding_model == settings.active_embedding_model,
        )
    )
    async with database.session_factory() as session:
        result = await session.execute(
            update(Document)
            .where(
                Document.status.in_([DocumentStatus.INDEXED, DocumentStatus.FAILED]),
                ~compatible_chunk,
            )
            .values(
                status=DocumentStatus.QUEUED,
                processed_at=None,
                error_message=None,
            )
        )
        await session.commit()
        requeued = result.rowcount or 0
    await database.dispose()
    get_database.cache_clear()
    return {
        "provider": settings.ai_provider,
        "embedding_model": settings.active_embedding_model,
        "documents_requeued": requeued,
        "next_step": "restart the API to process the durable queue",
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(requeue()), indent=2))

