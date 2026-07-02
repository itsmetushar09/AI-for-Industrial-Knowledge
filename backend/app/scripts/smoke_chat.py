"""Run self-cleaning semantic retrieval and citation verification."""

import asyncio
import json
import uuid

from sqlalchemy import delete

from app.core.config import get_settings
from app.database.session import get_database
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.rag.chat import PgVectorRetriever, RagChatService, RetrievedChunk


class DeterministicQuestionEmbedding:
    async def embed(
        self, _: list[str], *, task: str = "document"
    ) -> list[list[float]]:
        assert task == "query"
        return [[1.0] + [0.0] * 1535]


class DeterministicAnswer:
    async def answer(self, _: str, chunks: list[RetrievedChunk]) -> str:
        return f"The retrieved cause is: {chunks[0].content}"


async def smoke() -> dict[str, object]:
    """Insert vectors, retrieve them semantically, verify, and clean up."""

    database = get_database()
    settings = get_settings()
    if database.session_factory is None:
        raise RuntimeError("DATABASE_URL must be configured")

    first_document_id = uuid.uuid4()
    second_document_id = uuid.uuid4()
    try:
        async with database.session_factory() as session:
            session.add_all(
                [
                    Document(
                        id=first_document_id,
                        name="Pump Manual.pdf",
                        storage_path=f"smoke/{first_document_id}.pdf",
                        mime_type="application/pdf",
                        size_bytes=1,
                        status=DocumentStatus.INDEXED,
                    ),
                    Document(
                        id=second_document_id,
                        name="Unrelated Manual.pdf",
                        storage_path=f"smoke/{second_document_id}.pdf",
                        mime_type="application/pdf",
                        size_bytes=1,
                        status=DocumentStatus.INDEXED,
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=first_document_id,
                        chunk_index=0,
                        content="Cavitation caused by insufficient inlet pressure.",
                        token_count=8,
                        page_number=12,
                        embedding=[1.0] + [0.0] * 1535,
                        embedding_provider=settings.ai_provider,
                        embedding_model=settings.active_embedding_model,
                    ),
                    DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=second_document_id,
                        chunk_index=0,
                        content="Unrelated turbine maintenance schedule.",
                        token_count=6,
                        page_number=2,
                        embedding=[0.0, 1.0] + [0.0] * 1534,
                        embedding_provider=settings.ai_provider,
                        embedding_model=settings.active_embedding_model,
                    ),
                ]
            )
            await session.commit()

        async with database.session_factory() as session:
            service = RagChatService(
                DeterministicQuestionEmbedding(),
                PgVectorRetriever(
                    session,
                    settings.rag_top_k,
                    settings.ai_provider,
                    settings.active_embedding_model,
                ),
                DeterministicAnswer(),
            )
            response = await service.ask("Why did the pump fail?")
            verified = bool(
                response.citations
                and response.citations[0].document == "Pump Manual.pdf"
                and response.citations[0].page == 12
                and response.citations[0].score == 1.0
                and response.confidence >= 0.5
            )
        if not verified:
            raise RuntimeError("Phase 6 semantic retrieval verification failed")
        return {
            "status": "passed",
            "top_k": settings.rag_top_k,
            "top_document": response.citations[0].document,
            "top_page": response.citations[0].page,
            "top_similarity": response.citations[0].score,
            "citations": len(response.citations),
            "cleanup": True,
        }
    finally:
        async with database.session_factory() as session:
            await session.execute(
                delete(Document).where(Document.id.in_([first_document_id, second_document_id]))
            )
            await session.commit()
        await database.dispose()
        get_database.cache_clear()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(smoke()), indent=2))
