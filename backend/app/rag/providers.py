"""Select AI implementations without coupling application services to a vendor."""

from app.core.config import Settings
from app.core.gemini import get_gemini_clients
from app.core.openai import get_openai_clients
from app.rag.chat import AnswerProvider, OpenAIAnswerProvider
from app.rag.document_processing import EmbeddingProvider, OpenAIEmbeddingProvider
from app.rag.gemini import GeminiAnswerProvider, GeminiEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured embedding provider or raise when its key is absent."""

    if settings.ai_provider == "gemini":
        return GeminiEmbeddingProvider(get_gemini_clients().models(), settings)
    return OpenAIEmbeddingProvider(get_openai_clients().embeddings(), settings)


def build_answer_provider(settings: Settings) -> AnswerProvider:
    """Build the configured grounded-answer provider."""

    if settings.ai_provider == "gemini":
        return GeminiAnswerProvider(get_gemini_clients().models(), settings)
    return OpenAIAnswerProvider(get_openai_clients().embeddings(), settings)

