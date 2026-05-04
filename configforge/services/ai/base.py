from abc import ABC, abstractmethod


class LlmBackend(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...
