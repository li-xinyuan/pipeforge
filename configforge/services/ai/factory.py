from configforge.models.ai import AiProvider, AiSettings
from configforge.services.ai.base import LlmBackend


def create_backend(settings: AiSettings) -> LlmBackend:
    if settings.provider == AiProvider.ANTHROPIC:
        from configforge.services.ai.anthropic_backend import AnthropicBackend
        return AnthropicBackend(settings)
    else:
        from configforge.services.ai.openai_backend import OpenAiBackend
        return OpenAiBackend(settings)
