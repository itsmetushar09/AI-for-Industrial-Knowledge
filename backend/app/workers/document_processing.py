"""Persistent queue dispatch boundary for document processing."""

import logging
import uuid

from sqlalchemy import select

from app.core.supabase import get_supabase_clients
from app.database.session import get_database
from app.rag.document_processing import DocumentProcessingService
from app.rag.providers import build_embedding_provider
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.storage.service import SupabaseStorageService

logger = logging.getLogger(__name__)


async def dispatch_document_processing(document_id: uuid.UUID) -> None:
    """Process a durable queued document using independent service sessions."""

    logger.info(
        "Document processing dispatched",
        extra={"event": "document_processing_dispatched", "document_id": str(document_id)},
    )
    database = get_database()
    if database.session_factory is None:
        logger.error(
            "Document remains queued because the database is not configured",
            extra={"event": "document_processing_waiting_for_database", "document_id": str(document_id)},
        )
        return
    supabase = get_supabase_clients()
    settings = supabase.settings
    try:
        embeddings = build_embedding_provider(settings)
    except RuntimeError:
        logger.error(
            "Document remains queued because the AI provider is not configured",
            extra={
                "event": "document_processing_waiting_for_ai",
                "provider": settings.ai_provider,
                "document_id": str(document_id),
            },
        )
        return
    storage = SupabaseStorageService(supabase, supabase.settings)
    processor = DocumentProcessingService(
        database.session_factory,
        storage,
        embeddings,
        settings,
    )
    await processor.process(document_id)


async def recover_queued_documents(limit: int = 100) -> None:
    """Resume durable queued work after a server restart."""

    database = get_database()
    settings = get_supabase_clients().settings
    if database.session_factory is None or not settings.ai_configured:
        return

    async with database.session_factory() as session:
        document_ids = list(
            (
                await session.scalars(
                    select(Document.id)
                    .where(Document.status == DocumentStatus.QUEUED)
                    .order_by(Document.created_at)
                    .limit(limit)
                )
            ).all()
        )
    if document_ids:
        logger.info(
            "Recovering queued documents",
            extra={"event": "document_queue_recovery", "documents": len(document_ids)},
        )
    for document_id in document_ids:
        await dispatch_document_processing(document_id)
