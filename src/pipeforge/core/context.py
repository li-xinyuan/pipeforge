from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class InputStats(BaseModel):
    name: str
    rows_loaded: int
    elapsed_ms: float


class ProcessorStats(BaseModel):
    name: str
    tables_created: list[str]
    elapsed_ms: float


class OutputStats(BaseModel):
    rows_written: int
    file_path: str
    elapsed_ms: float


class ExecutionResult(BaseModel):
    inputs: dict[str, InputStats] = {}
    processors: list[ProcessorStats] = []
    output: OutputStats | None = None


@dataclass
class Logger:
    verbose: bool = False
    messages: list[dict[str, Any]] = field(default_factory=list)

    def info(self, msg: str) -> None:
        self.messages.append({"level": "INFO", "message": msg})

    def error(self, msg: str) -> None:
        self.messages.append({"level": "ERROR", "message": msg})

    def debug(self, msg: str) -> None:
        if self.verbose:
            self.messages.append({"level": "DEBUG", "message": msg})


@dataclass
class Context:
    db: "SQLiteManager"
    params: dict[str, str]
    yaml_dir: str
    scene_name: str
    output_path: str | None = None
    logger: Logger = field(default_factory=Logger)
    result: ExecutionResult = field(default_factory=ExecutionResult)
