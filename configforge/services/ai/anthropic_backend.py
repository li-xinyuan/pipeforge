from anthropic import AsyncAnthropic
from configforge.services.ai.base import LlmBackend


class AnthropicBackend(LlmBackend):
    def __init__(self, settings):
        from configforge.models.ai import AiSettings
        self._client = AsyncAnthropic(api_key=settings.api_key)
        self._model = settings.model or "claude-sonnet-4-6"
        self._max_tokens = settings.max_tokens
        self._temperature = settings.temperature

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
