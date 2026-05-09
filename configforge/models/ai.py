from enum import Enum
from pydantic import BaseModel
from typing import Literal


class AiProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class AiSettings(BaseModel):
    provider: AiProvider = AiProvider.OPENAI
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = False


class AiSettingsUpdate(BaseModel):
    """用于 PUT /settings — api_key=None 表示保留旧值，api_key="" 表示清空。"""
    provider: AiProvider = AiProvider.OPENAI
    api_key: str | None = None
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = False


class AiSuggestionRequest(BaseModel):
    category: Literal["scene", "columns", "sql", "mapping", "diagnose"]
    context: dict


class AiSuggestionResponse(BaseModel):
    content: str
    category: str
