import httpx
from anthropic import AsyncAnthropic

from configforge.services.ai.base import LlmBackend


class AnthropicBackend(LlmBackend):
    def __init__(self, settings):
        kwargs = {"api_key": settings.api_key, "http_client": httpx.AsyncClient(timeout=httpx.Timeout(60.0))}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self._client = AsyncAnthropic(**kwargs)
        self._model = settings.model or "claude-sonnet-4-6"
        self._max_tokens = settings.max_tokens
        self._temperature = settings.temperature

    async def close(self) -> None:
        if hasattr(self._client, "_client") and hasattr(self._client._client, "aclose"):
            await self._client._client.aclose()

    async def generate(self, prompt: str) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system="You are a helpful assistant. Always respond with valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.content[0].text if resp.content else ""
        return content
