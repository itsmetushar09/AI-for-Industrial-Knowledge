"""Page-aware PDF extraction, token chunking, embedding, and persistence."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

import fitz
import tiktoken
from openai import AsyncOpenAI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models.audit import AuditLog
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.storage.service import SupabaseStorageService

logger = logging.getLogger(__name__)
EmbeddingTask = Literal["document", "query"]


class DocumentProcessingError(Exception):
    """A deterministic document processing failure."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Normalized text extracted from one source PDF page."""

    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class TextChunk:
    """One token-bounded, page-addressable text chunk."""

    chunk_index: int
    page_number: int
    content: str
    token_count: int


class EmbeddingProvider(Protocol):
    """Embedding boundary used by production OpenAI and deterministic tests."""

    async def embed(
        self, texts: list[str], *, task: EmbeddingTask = "document"
    ) -> list[list[float]]:
        """Return one vector per input text, preserving order."""


class PdfTextExtractor:
    """Extract text from PDFs with PyMuPDF while retaining page numbers."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        """Return non-empty text pages or raise for unreadable PDFs."""

        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                pages = [
                    ExtractedPage(
                        page_number=index + 1,
                        text=page.get_text("text", sort=True).replace("\x00", "").strip(),
                    )
                    for index, page in enumerate(pdf)
                ]
        except Exception as exc:
            raise DocumentProcessingError("PDF text extraction failed") from exc

        pages = [page for page in pages if page.text]
        if not pages:
            raise DocumentProcessingError(
                "No extractable text was found; scanned PDFs require OCR support"
            )
        return pages


class TokenChunker:
    """Create fixed token windows with deterministic overlap per page."""

    def __init__(self, chunk_tokens: int, overlap_tokens: int) -> None:
        if overlap_tokens >= chunk_tokens:
            raise ValueError("overlap_tokens must be smaller than chunk_tokens")
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk(self, pages: list[ExtractedPage]) -> list[TextChunk]:
        """Split each page independently so every citation has one page."""

        chunks: list[TextChunk] = []
        step = self.chunk_tokens - self.overlap_tokens
        for page in pages:
            tokens = self.encoding.encode(page.text)
            for start in range(0, len(tokens), step):
                window = tokens[start : start + self.chunk_tokens]
                if not window:
                    continue
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        page_number=page.page_number,
                        content=self.encoding.decode(window),
                        token_count=len(window),
                    )
                )
                if start + self.chunk_tokens >= len(tokens):
                    break
        if not chunks:
            raise DocumentProcessingError("No text chunks were produced")
        return chunks


class OpenAIEmbeddingProvider:
    """Generate ordered embedding batches with the async OpenAI SDK."""

    def __init__(self, client: AsyncOpenAI, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def embed(
        self, texts: list[str], *, task: EmbeddingTask = "document"
    ) -> list[list[float]]:
        """Embed all texts in bounded batches and validate response dimensions."""

        vectors: list[list[float]] = []
        batch_size = self.settings.openai_embedding_batch_size
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = await self.client.embeddings.create(
                input=batch,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            if len(ordered) != len(batch):
                raise DocumentProcessingError("Embedding response count did not match input count")
            for item in ordered:
                vector = list(item.embedding)
                if len(vector) != self.settings.openai_embedding_dimensions:
                    raise DocumentProcessingError("Embedding response dimension is incompatible")
                vectors.append(vector)
        return vectors


class DocumentProcessingService:
    """Drive a queued document through extraction to indexed vectors."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: SupabaseStorageService,
        embeddings: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.embeddings = embeddings
        self.settings = settings
        self.extractor = PdfTextExtractor()
        self.chunker = TokenChunker(
            settings.document_chunk_tokens,
            settings.document_chunk_overlap,
        )

    async def process(self, document_id: uuid.UUID) -> bool:
        """Process one queued document idempotently and persist its final state."""

        started = time.perf_counter()

        document = await self._claim(document_id)
        if document is None:
            return False

        try:
            pdf_bytes = await self.storage.download(document.storage_path)
            pages = await asyncio.to_thread(self.extractor.extract, pdf_bytes)
            chunks = await asyncio.to_thread(self.chunker.chunk, pages)
            vectors = await self.embeddings.embed(
                [chunk.content for chunk in chunks], task="document"
            )
            if len(vectors) != len(chunks):
                raise DocumentProcessingError("Embedding count did not match chunk count")
            await self._persist(document_id, document, chunks, vectors)
        except Exception as exc:
            await self._mark_failed(document_id, exc)
            logger.exception(
                "Document processing failed",
                extra={
                    "event": "document_processing_failed",
                    "document_id": str(document_id),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return False

        logger.info(
            "Document processing completed",
            extra={
                "event": "document_processing_completed",
                "document_id": str(document_id),
                "chunks": len(chunks),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return True

    async def _claim(self, document_id: uuid.UUID) -> Document | None:
        """Atomically transition exactly one queued job to processing."""

        async with self.session_factory() as session:
            document = await session.scalar(
                select(Document).where(Document.id == document_id).with_for_update()
            )
            if document is None or document.status != DocumentStatus.QUEUED:
                return None
            document.status = DocumentStatus.PROCESSING
            document.error_message = None
            session.add(
                AuditLog(
                    action="document.processing_started",
                    entity_type="document",
                    entity_id=document_id,
                )
            )
            await session.commit()
            return document

    async def _persist(
        self,
        document_id: uuid.UUID,
        source: Document,
        chunks: list[TextChunk],
        vectors: list[list[float]],
    ) -> None:
        """Replace prior chunks and mark the document indexed in one transaction."""

        async with self.session_factory() as session:
            document = await session.scalar(
                select(Document).where(Document.id == document_id).with_for_update()
            )
            if document is None or document.status != DocumentStatus.PROCESSING:
                raise DocumentProcessingError("Document is no longer in processing state")

            await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk_id = uuid.uuid4()
                session.add(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        page_number=chunk.page_number,
                        embedding=vector,
                        embedding_provider=self.settings.ai_provider,
                        embedding_model=self.settings.active_embedding_model,
                        metadata_={
                            "page_number": chunk.page_number,
                            "filename": source.name,
                            "document_id": str(document_id),
                            "chunk_id": str(chunk_id),
                            "department": str(source.department_id) if source.department_id else None,
                        },
                    )
                )

            document.status = DocumentStatus.INDEXED
            document.processed_at = datetime.now(UTC)
            document.error_message = None
            session.add(
                AuditLog(
                    action="document.processing_completed",
                    entity_type="document",
                    entity_id=document_id,
                    details={"chunks": len(chunks)},
                )
            )
            await session.commit()

    async def _mark_failed(self, document_id: uuid.UUID, error: Exception) -> None:
        """Persist a bounded failure message in an independent transaction."""

        message = str(error).strip() or type(error).__name__
        async with self.session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = DocumentStatus.FAILED
            document.error_message = message[:2000]
            session.add(
                AuditLog(
                    action="document.processing_failed",
                    entity_type="document",
                    entity_id=document_id,
                    details={"error_type": type(error).__name__},
                )
            )
            await session.commit()
