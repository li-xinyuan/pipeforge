from pydantic import BaseModel
from typing import Literal, Optional


class AiSuggestionRequest(BaseModel):
    category: Literal["scene", "columns", "sql", "mapping"]
    context: dict  # context details vary by category


class AiSuggestionResponse(BaseModel):
    content: str
    category: str
