"""Document metadata, deletion, and semantic-search application service."""

import uuid
from typing import Annotated

from fastapi import Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.models.audit import AuditLog
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.rag.document_processing import EmbeddingProvider
from app.rag.providers import build_embedding_provider
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSearchHit,
    DocumentSummary,
)
from app.storage.service import SupabaseStorageService, get_storage_service


class DocumentServiceError(Exception):
    """Expected document operation failure with an HTTP-safe status."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentService:
    """Coordinate document records, private objects, and vector retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        storage: SupabaseStorageService,
        settings: Settings,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings
        self.embeddings = embeddings

    async def list_documents(
        self,
        page: int,
        page_size: int,
        document_status: DocumentStatus | None = None,
        department_id: uuid.UUID | None = None,
    ) -> DocumentListResponse:
        """Return a newest-first, optionally filtered document page."""

        filters = []
        if document_status is not None:
            filters.append(Document.status == document_status)
        if department_id is not None:
            filters.append(Document.department_id == department_id)

        total = int(
            await self.session.scalar(select(func.count(Document.id)).where(*filters)) or 0
        )
        statement = (
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        documents = (await self.session.scalars(statement)).all()
        return DocumentListResponse(
            items=[DocumentSummary.model_validate(document) for document in documents],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def detail(self, document_id: uuid.UUID) -> DocumentDetail:
        """Return one document and aggregate chunk/page counts."""

        document = await self.session.get(Document, document_id)
        if document is None:
            raise DocumentServiceError("Document not found", status.HTTP_404_NOT_FOUND)
        chunk_count, page_count = (
            await self.session.execute(
                select(
                    func.count(DocumentChunk.id),
                    func.count(func.distinct(DocumentChunk.page_number)),
                ).where(DocumentChunk.document_id == document_id)
            )
        ).one()
        return DocumentDetail(
            **DocumentSummary.model_validate(document).model_dump(),
            error_message=document.error_message,
            metadata=document.metadata_,
            chunk_count=int(chunk_count),
            page_count=int(page_count),
        )

    async def delete(self, document_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        """Remove the private object before deleting its database metadata."""

        document = await self.session.scalar(
            select(Document).where(Document.id == document_id).with_for_update()
        )
        if document is None:
            raise DocumentServiceError("Document not found", status.HTTP_404_NOT_FOUND)
        try:
            await self.storage.delete(document.storage_path)
        except Exception as exc:
            raise DocumentServiceError(
                "Document storage is temporarily unavailable",
                status.HTTP_502_BAD_GATEWAY,
            ) from exc

        self.session.add(
            AuditLog(
                actor_id=actor_id,
                action="document.deleted",
                entity_type="document",
                entity_id=document.id,
                details={"filename": document.name, "size_bytes": document.size_bytes},
            )
        )
        await self.session.delete(document)
        await self.session.commit()

    async def semantic_search(
        self,
        query: str,
        limit: int,
        department_id: uuid.UUID | None = None,
    ) -> list[DocumentSearchHit]:
        """Return vector-nearest chunks without any keyword-search fallback."""

        embeddings = self.embeddings
        if embeddings is None:
            try:
                embeddings = build_embedding_provider(self.settings)
            except RuntimeError as exc:
                raise DocumentServiceError(
                    f"{self.settings.ai_provider.title()} is not configured",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        try:
            vectors = await embeddings.embed([query], task="query")
        except Exception as exc:
            raise DocumentServiceError(
                "Semantic search is temporarily unavailable",
                status.HTTP_502_BAD_GATEWAY,
            ) from exc
        if len(vectors) != 1:
            raise DocumentServiceError(
                "Semantic search is temporarily unavailable",
                status.HTTP_502_BAD_GATEWAY,
            )

        distance = DocumentChunk.embedding.cosine_distance(vectors[0]).label("distance")
        filters = [
            Document.status == DocumentStatus.INDEXED,
            DocumentChunk.embedding.is_not(None),
            DocumentChunk.embedding_provider == self.settings.ai_provider,
            DocumentChunk.embedding_model == self.settings.active_embedding_model,
        ]
        if department_id is not None:
            filters.append(Document.department_id == department_id)
        statement = (
            select(
                DocumentChunk.document_id,
                Document.name,
                DocumentChunk.page_number,
                DocumentChunk.content,
                distance,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(*filters)
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            DocumentSearchHit(
                document_id=document_id,
                document=name,
                page=page_number,
                content=content,
                score=round(max(0.0, min(1.0, 1.0 - float(chunk_distance))), 4),
            )
            for document_id, name, page_number, content, chunk_distance in rows
        ]


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[SupabaseStorageService, Depends(get_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    """Inject document application operations."""

    return DocumentService(session, storage, settings)
