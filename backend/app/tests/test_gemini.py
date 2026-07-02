"""Gemini provider adapter tests."""

import math
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.rag.chat import RetrievedChunk
from app.rag.gemini import GeminiAnswerProvider, GeminiEmbeddingProvider


@pytest.mark.asyncio
async def test_gemini_embeddings_use_retrieval_task_and_normalize() -> None:
    captured: dict[str, object] = {}

    class FakeModels:
        async def embed_content(self, **kwargs: object) -> object:
            captured.update(kwargs)
            values = [3.0, 4.0] + [0.0] * 1534
            return SimpleNamespace(embeddings=[SimpleNamespace(values=values)])

    client = SimpleNamespace(aio=SimpleNamespace(models=FakeModels()))
    settings = Settings(gemini_api_key="test", _env_file=None)
    provider = GeminiEmbeddingProvider(client, settings)  # type: ignore[arg-type]
    [vector] = await provider.embed(["pump question"], task="query")

    config = captured["config"]
    assert getattr(config, "task_type") == "RETRIEVAL_QUERY"
    assert getattr(config, "output_dimensionality") == 1536
    assert len(vector) == 1536
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


@pytest.mark.asyncio
async def test_gemini_answer_uses_free_tier_model_and_grounded_instruction() -> None:
    captured: dict[str, object] = {}

    class FakeModels:
        async def generate_content(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(text="The pump failed because of cavitation.")

    client = SimpleNamespace(aio=SimpleNamespace(models=FakeModels()))
    settings = Settings(gemini_api_key="test", _env_file=None)
    provider = GeminiAnswerProvider(client, settings)  # type: ignore[arg-type]
    answer = await provider.answer(
        "Why did the pump fail?",
        [RetrievedChunk("Cavitation occurred.", "Pump.pdf", 12, 0.94)],
    )

    assert answer == "The pump failed because of cavitation."
    assert captured["model"] == "gemini-2.5-flash-lite"
    config = captured["config"]
    assert "untrusted reference data" in getattr(config, "system_instruction")
    assert "Cavitation occurred" in str(captured["contents"])


def test_gemini_is_the_default_ai_provider() -> None:
    settings = Settings(gemini_api_key="test", _env_file=None)
    assert settings.ai_provider == "gemini"
    assert settings.ai_configured
    assert settings.active_embedding_model == "gemini-embedding-001"

