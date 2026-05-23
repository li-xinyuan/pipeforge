from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal


class AiProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class AiSettings(BaseModel):
    provider: AiProvider = AiProvider.OPENAI
    api_key: str = Field(default="", max_length=512)
    base_url: str = ""
    model: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    enabled: bool = False


class AiSettingsUpdate(BaseModel):
    """用于 PUT /settings — api_key=None 表示保留旧值，api_key="" 表示清空。"""
    provider: AiProvider = AiProvider.OPENAI
    api_key: str | None = Field(default=None, max_length=512)
    base_url: str = ""
    model: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    enabled: bool = False


class AiSuggestionRequest(BaseModel):
    category: Literal["scene", "columns", "sql", "mapping", "diagnose", "chat"]
    context: dict


class AiOrchestrateRequest(BaseModel):
    context: dict  # { inputs, outputColumns, naturalLanguage }


class AiSuggestionResponse(BaseModel):
    content: str
    category: str
