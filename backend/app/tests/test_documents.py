"""Phase 8 document management and semantic-search tests."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.models.enums import DocumentStatus
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSearchHit,
    DocumentSummary,
)
from app.services.documents import DocumentService, DocumentServiceError, get_document_service
from app.models.document import Document


class FakeDocumentService:
    def __init__(self) -> None:
        self.document_id = uuid.uuid4()
        self.now = datetime.now(UTC)
        self.deleted: uuid.UUID | None = None
        self.search_query: str | None = None

    def summary(self) -> DocumentSummary:
        return DocumentSummary(
            id=self.document_id,
            name="Pump Manual.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            status=DocumentStatus.INDEXED,
            department_id=None,
            created_at=self.now,
            updated_at=self.now,
            processed_at=self.now,
        )

    async def list_documents(
        self,
        page: int,
        page_size: int,
        document_status: DocumentStatus | None,
        department_id: uuid.UUID | None,
    ) -> DocumentListResponse:
        assert (page, page_size) == (1, 25)
        assert document_status is None
        assert department_id is None
        return DocumentListResponse(items=[self.summary()], total=1, page=page, page_size=page_size)

    async def detail(self, document_id: uuid.UUID) -> DocumentDetail:
        assert document_id == self.document_id
        return DocumentDetail(
            **self.summary().model_dump(),
            error_message=None,
            metadata={"original_filename": "Pump Manual.pdf"},
            chunk_count=3,
            page_count=2,
        )

    async def delete(self, document_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        assert actor_id == uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        self.deleted = document_id

    async def semantic_search(
        self,
        query: str,
        limit: int,
        department_id: uuid.UUID | None,
    ) -> list[DocumentSearchHit]:
        self.search_query = query
        assert limit == 10
        assert department_id is None
        return [
            DocumentSearchHit(
                document_id=self.document_id,
                document="Pump Manual.pdf",
                page=4,
                content="Maintain adequate inlet pressure.",
                score=0.91,
            )
        ]


def test_document_api_contracts_and_static_search_route() -> None:
    service = FakeDocumentService()
    app.dependency_overrides[get_document_service] = lambda: service
    try:
        with TestClient(app) as client:
            listed = client.get("/documents")
            detailed = client.get(f"/documents/{service.document_id}")
            searched = client.get("/documents/search", params={"q": "  pump cavitation  "})
            deleted = client.delete(f"/documents/{service.document_id}")
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert detailed.status_code == 200
    assert detailed.json()["chunk_count"] == 3
    assert searched.status_code == 200
    assert searched.json()[0]["score"] == 0.91
    assert service.search_query == "pump cavitation"
    assert deleted.status_code == 204
    assert service.deleted == service.document_id


class FakeEmbeddings:
    async def embed(
        self, texts: list[str], *, task: str = "document"
    ) -> list[list[float]]:
        assert texts == ["pump failure"]
        assert task == "query"
        return [[1.0] + [0.0] * 1535]


class FakeRows:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self.rows


class SearchSession:
    def __init__(self, row: tuple[object, ...]) -> None:
        self.row = row

    async def execute(self, _: object) -> FakeRows:
        return FakeRows([self.row])


@pytest.mark.asyncio
async def test_semantic_search_uses_query_embedding_and_vector_score() -> None:
    document_id = uuid.uuid4()
    service = DocumentService(
        SearchSession(
            (document_id, "Pump Manual.pdf", 7, "Inspect the inlet line.", 0.08)
        ),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        Settings(_env_file=None),
        embeddings=FakeEmbeddings(),  # type: ignore[arg-type]
    )

    results = await service.semantic_search("pump failure", 5)

    assert len(results) == 1
    assert results[0].document_id == document_id
    assert results[0].score == 0.92


@pytest.mark.asyncio
async def test_delete_keeps_metadata_when_storage_is_unavailable() -> None:
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        name="Pump Manual.pdf",
        storage_path=f"{document_id}/Pump Manual.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        status=DocumentStatus.INDEXED,
    )

    class DeleteSession:
        deleted = False

        async def scalar(self, _: object) -> Document:
            return document

        async def delete(self, _: object) -> None:
            self.deleted = True

    class UnavailableStorage:
        async def delete(self, _: str) -> None:
            raise RuntimeError("storage unavailable")

    session = DeleteSession()
    service = DocumentService(
        session,  # type: ignore[arg-type]
        UnavailableStorage(),  # type: ignore[arg-type]
        Settings(_env_file=None),
    )

    with pytest.raises(DocumentServiceError) as error:
        await service.delete(document_id, uuid.uuid4())

    assert error.value.status_code == 502
    assert not session.deleted
