"""Phase 5 extraction, chunking, and embedding tests."""

from types import SimpleNamespace

import fitz
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.rag.document_processing import (
    DocumentProcessingError,
    ExtractedPage,
    OpenAIEmbeddingProvider,
    PdfTextExtractor,
    TokenChunker,
)


def pdf_with_pages(*page_texts: str) -> bytes:
    document = fitz.open()
    try:
        for text in page_texts:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def test_extracts_page_aware_pdf_text() -> None:
    pages = PdfTextExtractor().extract(pdf_with_pages("Pump manual", "Safety procedure"))
    assert [(page.page_number, page.text) for page in pages] == [
        (1, "Pump manual"),
        (2, "Safety procedure"),
    ]


def test_rejects_pdf_without_extractable_text() -> None:
    with pytest.raises(DocumentProcessingError, match="No extractable text"):
        PdfTextExtractor().extract(pdf_with_pages(""))


def test_chunks_at_800_tokens_with_150_token_overlap() -> None:
    chunker = TokenChunker(chunk_tokens=800, overlap_tokens=150)
    token_id = chunker.encoding.encode(" pump")[0]
    token_ids = [token_id] * 1000
    page_text = chunker.encoding.decode(token_ids)
    chunks = chunker.chunk([ExtractedPage(page_number=7, text=page_text)])

    assert len(chunks) == 2
    assert chunks[0].token_count == 800
    assert chunks[1].token_count == 350
    assert chunks[0].page_number == chunks[1].page_number == 7
    first = chunker.encoding.encode(chunks[0].content)
    second = chunker.encoding.encode(chunks[1].content)
    assert first[-150:] == second[:150]


@pytest.mark.asyncio
async def test_openai_embeddings_are_batched_ordered_and_dimension_checked() -> None:
    calls: list[dict[str, object]] = []

    class FakeEmbeddings:
        async def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            inputs = kwargs["input"]
            assert isinstance(inputs, list)
            data = [
                SimpleNamespace(index=index, embedding=[float(index)] * 1536)
                for index in reversed(range(len(inputs)))
            ]
            return SimpleNamespace(data=data)

    client = SimpleNamespace(embeddings=FakeEmbeddings())
    settings = Settings(openai_embedding_batch_size=2, _env_file=None)
    provider = OpenAIEmbeddingProvider(client, settings)  # type: ignore[arg-type]
    vectors = await provider.embed(["one", "two", "three"])

    assert len(calls) == 2
    assert all(call["model"] == "text-embedding-3-small" for call in calls)
    assert all(call["dimensions"] == 1536 for call in calls)
    assert len(vectors) == 3
    assert all(len(vector) == 1536 for vector in vectors)


def test_rag_configuration_rejects_invalid_overlap() -> None:
    with pytest.raises(ValidationError, match="smaller than"):
        Settings(document_chunk_tokens=800, document_chunk_overlap=800, _env_file=None)
