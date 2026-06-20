"""Persistent rate limiter with file-based storage and file locking.

Supports multi-worker deployments by storing rate-limit state in a shared
JSON file protected by ``fcntl`` file locks (via ``utils.file_lock``).
Expired records are cleaned up on every ``is_allowed`` call.
"""
import fcntl
import json
import logging
import os
import time
from typing import Optional

from configforge.utils.paths import get_data_dir

logger = logging.getLogger("configforge.rate_limit")


class RateLimiter:
    """File-backed sliding-window rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed within *window_seconds*.
    window_seconds:
        Sliding window duration in seconds.
    storage_path:
        Path to the JSON file used for persistence.  Defaults to
        ``<data_dir>/rate_limit.json``.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        storage_path: Optional[str] = None,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        if storage_path is None:
            storage_path = os.path.join(get_data_dir(), "rate_limit.json")
        self.storage_path = storage_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, key: str) -> bool:
        """Check whether *key* is allowed to make a request.

        Returns ``True`` and records the timestamp if the request is within
        the rate limit; returns ``False`` otherwise.  Expired entries are
        cleaned up as a side-effect.
        """
        state = self._load_state()
        state = self._cleanup_expired(state)
        now = time.time()
        timestamps = state.get(key, [])
        # Count requests within the current window
        window_start = now - self.window_seconds
        timestamps = [t for t in timestamps if t > window_start]
        if len(timestamps) >= self.max_requests:
            # Still save the cleaned state so expired keys don't accumulate
            state[key] = timestamps
            self._save_state(state)
            return False
        timestamps.append(now)
        state[key] = timestamps
        self._save_state(state)
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        """Load rate-limit state from the JSON file (with shared lock)."""
        if not os.path.exists(self.storage_path):
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                except (json.JSONDecodeError, ValueError):
                    return {}
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError:
            return {}

    def _save_state(self, state: dict) -> None:
        """Persist *state* to the JSON file (with exclusive lock)."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(state, f, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            logger.warning("Failed to persist rate-limit state: %s", exc)

    def _cleanup_expired(self, state: dict) -> dict:
        """Remove timestamps outside the sliding window for every key.

        Keys with no remaining timestamps are removed entirely to prevent
        unbounded growth of the state file.
        """
        cutoff = time.time() - self.window_seconds
        cleaned: dict = {}
        for key, timestamps in state.items():
            remaining = [t for t in timestamps if t > cutoff]
            if remaining:
                cleaned[key] = remaining
        return cleaned
