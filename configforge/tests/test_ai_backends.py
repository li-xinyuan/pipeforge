from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configforge.models.ai import AiProvider, AiSettings
from configforge.services.ai.anthropic_backend import AnthropicBackend
from configforge.services.ai.factory import create_backend
from configforge.services.ai.openai_backend import OpenAiBackend


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


@patch("configforge.services.ai.openai_backend.AsyncOpenAI")
def test_openai_uses_custom_model(mock_async_openai):
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test", model="gpt-4o-mini")
    backend = OpenAiBackend(settings)
    assert backend._model == "gpt-4o-mini"


@patch("configforge.services.ai.openai_backend.AsyncOpenAI")
def test_openai_uses_default_model(mock_async_openai):
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = OpenAiBackend(settings)
    assert backend._model == "gpt-4o"


@patch("configforge.services.ai.anthropic_backend.AsyncAnthropic")
def test_anthropic_uses_custom_model(mock_async_anthropic):
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test", model="claude-3-haiku-20240307")
    backend = AnthropicBackend(settings)
    assert backend._model == "claude-3-haiku-20240307"


@patch("configforge.services.ai.anthropic_backend.AsyncAnthropic")
def test_anthropic_uses_default_model(mock_async_anthropic):
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = AnthropicBackend(settings)
    assert backend._model == "claude-sonnet-4-6"


@patch("configforge.services.ai.openai_backend.AsyncOpenAI")
def test_openai_with_base_url(mock_async_openai):
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test", base_url="http://localhost:8080")
    OpenAiBackend(settings)
    mock_async_openai.assert_called_once()
    call_kwargs = mock_async_openai.call_args[1]
    assert call_kwargs["base_url"] == "http://localhost:8080"


@patch("configforge.services.ai.anthropic_backend.AsyncAnthropic")
def test_anthropic_with_base_url(mock_async_anthropic):
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test", base_url="http://localhost:8080")
    AnthropicBackend(settings)
    mock_async_anthropic.assert_called_once()
    call_kwargs = mock_async_anthropic.call_args[1]
    assert call_kwargs["base_url"] == "http://localhost:8080"


@pytest.mark.anyio
async def test_openai_generate_empty_content():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = OpenAiBackend(settings)
    backend._client = MagicMock()
    backend._client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=None))]
    ))
    result = await backend.generate("test prompt")
    assert result == ""


@pytest.mark.anyio
async def test_anthropic_generate_empty_content():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = AnthropicBackend(settings)
    backend._client = MagicMock()
    backend._client.messages.create = AsyncMock(return_value=MagicMock(content=[]))
    result = await backend.generate("test prompt")
    assert result == ""


@pytest.mark.anyio
async def test_openai_close():
    settings = AiSettings(provider=AiProvider.OPENAI, api_key="sk-test")
    backend = OpenAiBackend(settings)
    backend._client = MagicMock()
    backend._client._client = MagicMock()
    backend._client._client.aclose = AsyncMock()
    await backend.close()
    backend._client._client.aclose.assert_awaited_once()


@pytest.mark.anyio
async def test_anthropic_close():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test")
    backend = AnthropicBackend(settings)
    backend._client = MagicMock()
    backend._client._client = MagicMock()
    backend._client._client.aclose = AsyncMock()
    await backend.close()
    backend._client._client.aclose.assert_awaited_once()


def test_factory_invalid_provider_defaults_to_openai():
    settings = AiSettings(provider=AiProvider.CUSTOM, api_key="sk-test")
    backend = create_backend(settings)
    assert isinstance(backend, OpenAiBackend)
