from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NotifyContext:
    """Context for a notification dispatch."""
    execution_id: str
    config_name: str
    status: str  # success / failed / anomaly
    summary: str
    output_files: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    error_message: str | None = None
    # Enhanced fields (T-5D-04)
    duration_seconds: float | None = None
    row_count: int | None = None
    error_type: str | None = None
    stack_summary: str | None = None


@dataclass
class NotifyResult:
    """Result of a notification dispatch."""
    success: bool
    message: str
    provider: str


class NotifierBase(ABC):
    """Abstract base class for notification notifiers."""

    @abstractmethod
    async def send(self, context: NotifyContext) -> NotifyResult: ...
