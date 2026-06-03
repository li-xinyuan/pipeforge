import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pipeforge.config.models import CheckResult


class InputStats(BaseModel):
    name: str
    rows_loaded: int
    elapsed_ms: float


class ProcessorStats(BaseModel):
    name: str
    tables_created: list[str] = []
    elapsed_ms: float


class OutputStats(BaseModel):
    rows_written: int
    file_path: str
    elapsed_ms: float


class ExecutionResult(BaseModel):
    inputs: dict[str, InputStats] = {}
    processors: list[ProcessorStats] = []
    output: OutputStats | None = None
    checks: list[CheckResult] = []


@dataclass
class Logger:
    verbose: bool = False
    log_dir: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    _file: Any = None

    def __post_init__(self):
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self._file = open(os.path.join(self.log_dir, f"pipeforge_{ts}.log"), "w")

    def _write(self, level: str, msg: str) -> None:
        self.messages.append({"level": level, "message": msg})
        if self._file:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._file.write(f"[{ts}] [{level}] {msg}\n")
            self._file.flush()

    def info(self, msg: str) -> None:
        self._write("INFO", msg)

    def error(self, msg: str) -> None:
        self._write("ERROR", msg)

    def debug(self, msg: str) -> None:
        if self.verbose:
            self._write("DEBUG", msg)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None


@dataclass
class Context:
    db: "SQLiteManager"
    params: dict[str, str]
    yaml_dir: str
    scene_name: str
    output_path: str | None = None
    logger: Logger = field(default_factory=Logger)
    result: ExecutionResult = field(default_factory=ExecutionResult)
