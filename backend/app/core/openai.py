"""OpenAI async client lifecycle and dependency injection."""

from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings


class OpenAIClients:
    """Lazily initialize the server-side OpenAI client."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: AsyncOpenAI | None = None

    def embeddings(self) -> AsyncOpenAI:
        """Return a configured client or fail without exposing credentials."""

        if self.settings.openai_api_key is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.openai_api_key.get_secret_value(),
                timeout=self.settings.openai_request_timeout,
                max_retries=3,
            )
        return self._client

    async def close(self) -> None:
        """Close the client transport if it was initialized."""

        if self._client is not None:
            await self._client.close()


@lru_cache
def get_openai_clients() -> OpenAIClients:
    """Return the process-wide OpenAI client manager."""

    return OpenAIClients()
