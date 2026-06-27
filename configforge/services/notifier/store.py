"""通知配置与历史持久化层。

从 api/notifications.py 抽取，解除 service→api 反向依赖。
"""
import fcntl
import json
from pathlib import Path

from configforge.models.notification import (
    NotificationConfig,
    NotificationHistoryEntry,
)
from configforge.utils.migration import load_with_migration
from configforge.utils.paths import get_data_dir

_DATA_DIR = get_data_dir()
NOTIFICATIONS_PATH = Path(_DATA_DIR) / "notifications.json"
HISTORY_PATH = Path(_DATA_DIR) / "notification_history.json"


def load_notifications() -> list[NotificationConfig]:
    NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = load_with_migration(str(NOTIFICATIONS_PATH), default=[])
    if isinstance(data, list):
        return [NotificationConfig(**item) for item in data]
    return [NotificationConfig(**item) for item in data.get("notifications", [])]


def save_notifications(configs: list[NotificationConfig]) -> None:
    NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = NOTIFICATIONS_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump([c.model_dump() for c in configs], f, ensure_ascii=False, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.replace(NOTIFICATIONS_PATH)


def load_history() -> list[NotificationHistoryEntry]:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = load_with_migration(str(HISTORY_PATH), default=[])
    if isinstance(data, list):
        return [NotificationHistoryEntry(**item) for item in data]
    return [NotificationHistoryEntry(**item) for item in data.get("history", [])]


def save_history(entries: list[NotificationHistoryEntry]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Keep only last 200 entries
    entries = entries[-200:]
    tmp = HISTORY_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump([e.model_dump() for e in entries], f, ensure_ascii=False, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.replace(HISTORY_PATH)


def add_history_entry(entry: NotificationHistoryEntry) -> None:
    """Add a notification history entry (called by dispatcher)."""
    history = load_history()
    history.append(entry)
    save_history(history)
