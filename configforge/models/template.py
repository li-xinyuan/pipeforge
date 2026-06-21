from typing import Literal

from pydantic import BaseModel, ConfigDict


class TemplateRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["database", "ai", "input_format"]
    description: str


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    category: str  # "sales" / "finance" / "hr" / "ops" / "general"
    tags: list[str] = []
    author: str = ""
    version: str = "1.0"
    config_state: dict  # Complete WizardState JSON
    requirements: list[TemplateRequirement] = []
    usage_count: int = 0
    is_official: bool = False
    created_at: str = ""
    updated_at: str = ""
