"""Run self-cleaning Phase 5 processing against Supabase and pgvector."""

import asyncio
import json
import uuid

import fitz
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.supabase import get_supabase_clients
from app.database.session import get_database
from app.models.audit import AuditLog
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.rag.document_processing import DocumentProcessingService
from app.storage.service import SupabaseStorageService


class DeterministicEmbeddings:
    """Cost-free vectors for infrastructure verification only."""

    async def embed(
        self, texts: list[str], *, task: str = "document"
    ) -> list[list[float]]:
        assert task == "document"
        vectors: list[list[float]] = []
        for index, _ in enumerate(texts):
            vector = [0.0] * 1536
            vector[index % 1536] = 1.0
            vectors.append(vector)
        return vectors


def sample_pdf() -> bytes:
    """Create a valid two-page industrial PDF entirely in memory."""

    document = fitz.open()
    try:
        first = document.new_page()
        first.insert_text((72, 72), "Pump A maintenance requires weekly lubrication checks.")
        second = document.new_page()
        second.insert_text((72, 72), "Cavitation can result from insufficient inlet pressure.")
        return document.tobytes()
    finally:
        document.close()


async def smoke() -> dict[str, object]:
    """Process, verify, and remove one deterministic document."""

    settings = get_settings()
    database = get_database()
    clients = get_supabase_clients()
    if database.session_factory is None:
        raise RuntimeError("DATABASE_URL must be configured")
    storage = SupabaseStorageService(clients, settings)
    document_id = uuid.uuid4()
    storage_path = f"{document_id}/phase-5-smoke.pdf"
    pdf_bytes = sample_pdf()

    try:
        await storage.upload(storage_path, pdf_bytes, "application/pdf")
        async with database.session_factory() as session:
            session.add(
                Document(
                    id=document_id,
                    name="phase-5-smoke.pdf",
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    size_bytes=len(pdf_bytes),
                    status=DocumentStatus.QUEUED,
                )
            )
            await session.commit()

        processor = DocumentProcessingService(
            database.session_factory,
            storage,
            DeterministicEmbeddings(),
            settings,
        )
        processed = await processor.process(document_id)

        async with database.session_factory() as session:
            document = await session.get(Document, document_id)
            chunks = list(
                (
                    await session.scalars(
                        select(DocumentChunk)
                        .where(DocumentChunk.document_id == document_id)
                        .order_by(DocumentChunk.chunk_index)
                    )
                ).all()
            )
            verified = bool(
                processed
                and document is not None
                and document.status == DocumentStatus.INDEXED
                and document.processed_at is not None
                and len(chunks) == 2
                and all(chunk.embedding is not None and len(chunk.embedding) == 1536 for chunk in chunks)
                and all(chunk.embedding_provider == settings.ai_provider for chunk in chunks)
                and all(chunk.embedding_model == settings.active_embedding_model for chunk in chunks)
                and [chunk.page_number for chunk in chunks] == [1, 2]
            )
        if not verified:
            raise RuntimeError("Phase 5 persistence verification failed")

        return {
            "status": "passed",
            "pages": 2,
            "chunks": len(chunks),
            "embedding_dimensions": 1536,
            "document_status": "indexed",
            "cleanup": True,
        }
    finally:
        try:
            await storage.delete(storage_path)
        except Exception:
            pass
        async with database.session_factory() as session:
            await session.execute(
                delete(AuditLog).where(
                    AuditLog.entity_type == "document", AuditLog.entity_id == document_id
                )
            )
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.commit()
        await clients.close()
        await database.dispose()
        get_supabase_clients.cache_clear()
        get_database.cache_clear()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(smoke()), indent=2))
