import pytest
from unittest.mock import AsyncMock, MagicMock
from configforge.models.ai import AiSettings, AiProvider
from configforge.services.ai.factory import create_backend
from configforge.services.ai.openai_backend import OpenAiBackend
from configforge.services.ai.anthropic_backend import AnthropicBackend


def test_factory_creates_openai():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = create_backend(settings)
    assert isinstance(backend, OpenAiBackend)


def test_factory_creates_anthropic():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = create_backend(settings)
    assert isinstance(backend, AnthropicBackend)


def test_factory_creates_openai_for_custom():
    settings = AiSettings(provider=AiProvider.CUSTOM, api_key="sk-test", base_url="http://localhost:8080")
    backend = create_backend(settings)
    assert isinstance(backend, OpenAiBackend)


@pytest.mark.anyio
async def test_openai_generate_mock():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = OpenAiBackend(settings)
    backend._client = MagicMock()
    backend._client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"sql": "SELECT 1"}'))]
    ))
    result = await backend.generate("test prompt")
    assert "SELECT 1" in result


@pytest.mark.anyio
async def test_anthropic_generate_mock():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = AnthropicBackend(settings)
    backend._client = MagicMock()
    backend._client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"sql": "SELECT 1"}')]
    ))
    result = await backend.generate("test prompt")
    assert "SELECT 1" in result
