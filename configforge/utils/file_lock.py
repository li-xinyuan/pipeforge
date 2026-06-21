"""Thread-safe JSON file operations with file locking."""
import fcntl
import json
from typing import Any


def read_json_locked(path: str) -> Any:
    """Read JSON file with shared lock."""
    with open(path, encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def write_json_locked(path: str, data: Any) -> None:
    """Write JSON file with exclusive lock."""
    with open(path, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
