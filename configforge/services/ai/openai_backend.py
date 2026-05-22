import httpx
from openai import AsyncOpenAI
from configforge.services.ai.base import LlmBackend


class OpenAiBackend(LlmBackend):
    def __init__(self, settings):
        kwargs: dict = {"api_key": settings.api_key, "http_client": httpx.AsyncClient(timeout=httpx.Timeout(60.0))}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.model or "gpt-4o"
        self._temperature = settings.temperature
        self._max_tokens = settings.max_tokens

    async def close(self) -> None:
        if hasattr(self._client, "_client") and hasattr(self._client._client, "aclose"):
            await self._client._client.aclose()

    async def generate(self, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return resp.choices[0].message.content or ""
