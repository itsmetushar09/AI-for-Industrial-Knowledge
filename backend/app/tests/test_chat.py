"""Phase 6 grounded chat tests."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.chat import get_chat_service, get_history_service
from app.core.config import Settings
from app.rag.chat import OpenAIAnswerProvider, RagChatService, RetrievedChunk
from app.services.conversation_history import ConversationNotFoundError


class FakeEmbeddings:
    async def embed(
        self, texts: list[str], *, task: str = "document"
    ) -> list[list[float]]:
        assert len(texts) == 1
        assert task == "query"
        return [[1.0] + [0.0] * 1535]


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks

    async def retrieve(self, embedding: list[float]) -> list[RetrievedChunk]:
        assert len(embedding) == 1536
        return self.chunks


class FakeAnswers:
    def __init__(self) -> None:
        self.called = False

    async def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        self.called = True
        assert question
        assert chunks
        return "Cavitation resulted from insufficient inlet pressure."


class FakeHistory:
    def __init__(self) -> None:
        self.conversation_id = uuid4()
        self.recorded: tuple[str, object] | None = None

    async def claim_anonymous(self, session_id: UUID | None, user_id: UUID) -> None:
        assert user_id == UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    async def assert_access(self, conversation_id: UUID, session_id: UUID) -> None:
        assert conversation_id == self.conversation_id
        assert session_id

    async def record_exchange(
        self,
        session_id: UUID,
        question: str,
        response: object,
        conversation_id: UUID | None = None,
    ) -> UUID:
        assert session_id
        self.recorded = (question, response)
        return conversation_id or self.conversation_id

    async def history(self, session_id: UUID) -> list[object]:
        assert session_id
        return []

    async def delete(self, conversation_id: UUID, session_id: UUID) -> None:
        assert conversation_id == self.conversation_id
        assert session_id


@pytest.mark.asyncio
async def test_chat_returns_confidence_and_deduplicated_citations() -> None:
    chunks = [
        RetrievedChunk("first", "Pump Manual.pdf", 12, 0.94),
        RetrievedChunk("second", "Pump Manual.pdf", 12, 0.90),
        RetrievedChunk("third", "Inspection.pdf", 4, 0.82),
    ]
    service = RagChatService(FakeEmbeddings(), FakeRetriever(chunks), FakeAnswers())
    response = await service.ask("Why did the pump fail?")

    assert response.confidence == 0.8867
    assert [(citation.document, citation.page) for citation in response.citations] == [
        ("Pump Manual.pdf", 12),
        ("Inspection.pdf", 4),
    ]
    assert response.citations[0].score == 0.94


@pytest.mark.asyncio
async def test_chat_does_not_generate_without_sources() -> None:
    answers = FakeAnswers()
    service = RagChatService(FakeEmbeddings(), FakeRetriever([]), answers)
    response = await service.ask("Unknown question")

    assert response.confidence == 0
    assert response.citations == []
    assert "could not find" in response.answer
    assert not answers.called


@pytest.mark.asyncio
async def test_responses_api_prompt_is_grounded_and_not_stored() -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        async def create(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(output_text="Grounded answer")

    client = SimpleNamespace(responses=FakeResponses())
    provider = OpenAIAnswerProvider(client, Settings(_env_file=None))  # type: ignore[arg-type]
    answer = await provider.answer(
        "What failed?",
        [RetrievedChunk("Bearing seizure", "Report.pdf", 3, 0.91)],
    )

    assert answer == "Grounded answer"
    assert captured["model"] == "gpt-5.4-mini"
    assert captured["store"] is False
    assert "Bearing seizure" in str(captured["input"])
    assert "untrusted reference data" in str(captured["instructions"])


def test_chat_endpoint_contract() -> None:
    chunks = [RetrievedChunk("source", "Manual.pdf", 2, 0.9)]
    service = RagChatService(FakeEmbeddings(), FakeRetriever(chunks), FakeAnswers())
    history = FakeHistory()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_history_service] = lambda: history
    try:
        with TestClient(app) as client:
            response = client.post("/chat", json={"question": "Why did Pump A fail?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Cavitation resulted from insufficient inlet pressure.",
        "confidence": 0.9,
        "citations": [{"document": "Manual.pdf", "page": 2, "score": 0.9}],
        "conversation_id": str(history.conversation_id),
    }
    assert history.recorded is not None


def test_chat_history_and_delete_share_browser_session() -> None:
    history = FakeHistory()
    app.dependency_overrides[get_history_service] = lambda: history
    try:
        with TestClient(app) as client:
            history_response = client.get("/chat/history")
            delete_response = client.delete(f"/chat/{history.conversation_id}")
    finally:
        app.dependency_overrides.clear()

    assert history_response.status_code == 200
    assert history_response.json() == []
    assert delete_response.status_code == 204


def test_unknown_conversation_is_rejected_before_ai_call() -> None:
    class MissingHistory(FakeHistory):
        async def assert_access(self, conversation_id: UUID, user_id: UUID) -> None:
            raise ConversationNotFoundError

        async def record_exchange(self, *_: object, **__: object) -> UUID:
            raise AssertionError("missing conversation must not be persisted")

    class UnusedChatService:
        async def ask(self, _: str) -> object:
            raise AssertionError("AI must not run for an inaccessible conversation")

    history = MissingHistory()
    app.dependency_overrides[get_chat_service] = lambda: UnusedChatService()
    app.dependency_overrides[get_history_service] = lambda: history
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "question": "Why did the pump fail?",
                    "conversation_id": str(history.conversation_id),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}
