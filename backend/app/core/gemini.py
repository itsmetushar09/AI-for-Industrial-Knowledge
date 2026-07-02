"""Google Gemini async client lifecycle."""

from functools import lru_cache

from google import genai

from app.core.config import get_settings


class GeminiClients:
    """Lazily initialize the Gemini Developer API client."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: genai.Client | None = None

    def models(self) -> genai.Client:
        """Return a configured client without exposing its API key."""

        if self.settings.gemini_api_key is None:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        if self._client is None:
            self._client = genai.Client(
                api_key=self.settings.gemini_api_key.get_secret_value()
            )
        return self._client

    async def close(self) -> None:
        """Close Gemini's async transport when initialized."""

        if self._client is not None:
            await self._client.aio.aclose()


@lru_cache
def get_gemini_clients() -> GeminiClients:
    """Return the process-wide Gemini client manager."""

    return GeminiClients()

