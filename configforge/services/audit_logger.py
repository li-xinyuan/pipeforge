"""Audit logging for critical operations."""

import os
from datetime import UTC, datetime

from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.paths import get_data_dir

AUDIT_LOG_PATH = os.path.join(get_data_dir(), "audit_log.json")
MAX_AUDIT_ENTRIES = 10000


def log_audit(action: str, target_type: str, target_id: str, details: dict | None = None) -> None:
    """Log an audit entry for a critical operation."""
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,           # create/update/delete/execute
        "target_type": target_type,  # config/connection/template/schedule
        "target_id": target_id,
        "details": details or {},
    }

    # Load existing log
    entries = _load_entries()
    entries.append(entry)

    # Trim if too large
    if len(entries) > MAX_AUDIT_ENTRIES:
        entries = entries[-MAX_AUDIT_ENTRIES:]

    # Save back
    _save_entries(entries)


def get_audit_log(
    target_type: str | None = None,
    action: str | None = None,
    limit: int = 100,
    user: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict]:
    """Query audit log entries with optional filters."""
    entries = _load_entries()

    if target_type:
        entries = [e for e in entries if e.get("target_type") == target_type]
    if action:
        entries = [e for e in entries if e.get("action") == action]
    if user:
        entries = [e for e in entries if e.get("target_id") == user or e.get("details", {}).get("user") == user]
    if start_time:
        entries = [e for e in entries if e.get("timestamp", "") >= start_time]
    if end_time:
        entries = [e for e in entries if e.get("timestamp", "") <= end_time]

    return entries[-limit:]


def _load_entries() -> list[dict]:
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    try:
        return read_json_locked(AUDIT_LOG_PATH)
    except Exception:
        return []


def _save_entries(entries: list[dict]) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    write_json_locked(AUDIT_LOG_PATH, entries)
