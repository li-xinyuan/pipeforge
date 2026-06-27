"""Persistent rate limiter with file-based or database storage.

T-5E-04: 当 SQL 后端（SQLite/PostgreSQL）激活时，限流状态存储在数据库中，
支持多实例跨主机部署。JSON 后端继续使用文件 + fcntl 文件锁（单机）。
Expired records are cleaned up on every ``is_allowed`` call.
"""
import fcntl
import json
import logging
import os
import random
import time

from configforge.utils.paths import get_data_dir

logger = logging.getLogger("configforge.rate_limit")


class RateLimiter:
    """Sliding-window rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed within *window_seconds*.
    window_seconds:
        Sliding window duration in seconds.
    storage_path:
        Path to the JSON file used for persistence (JSON backend only).
        Defaults to ``<data_dir>/rate_limit.json``.

    T-5E-04: 当 CONFIGFORGE_STORAGE_BACKEND 为 sqlite/postgresql 时，
    自动切换到数据库存储，限流状态跨实例共享。
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        storage_path: str | None = None,
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
        the rate limit; returns ``False`` otherwise.

        T-5E-04: SQL 后端使用数据库事务（跨实例共享），JSON 后端使用文件锁。
        """
        if self._is_sql_backend():
            return self._is_allowed_sql(key)
        return self._is_allowed_file(key)

    # ------------------------------------------------------------------
    # Backend detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_sql_backend() -> bool:
        """Check if SQL backend (sqlite/postgresql) is active."""
        backend = os.environ.get("CONFIGFORGE_STORAGE_BACKEND", "json").lower()
        return backend in ("sqlite", "postgresql")

    # ------------------------------------------------------------------
    # SQL backend implementation (T-5E-04)
    # ------------------------------------------------------------------

    def _is_allowed_sql(self, key: str) -> bool:
        """Check rate limit using database storage.

        Uses a database transaction for atomicity. Per-key cleanup of
        expired entries is done on each call. A probabilistic global
        cleanup (1% chance) prevents unbounded growth from inactive keys.

        Race condition: two instances might both allow a request that
        should be rate-limited (off by 1). This is acceptable for rate
        limiting — the important property is that both instances see the
        same count.
        """
        try:
            from sqlalchemy import delete, func, insert, select

            from configforge.storage.sql_schema import get_engine, rate_limit_table

            engine = get_engine()
            now = time.time()
            window_start = now - self.window_seconds

            with engine.begin() as conn:
                # Per-key cleanup: remove expired entries for this key
                conn.execute(
                    delete(rate_limit_table).where(
                        rate_limit_table.c.key == key,
                        rate_limit_table.c.timestamp <= window_start,
                    )
                )

                # Probabilistic global cleanup (1% chance) for inactive keys
                if random.random() < 0.01:
                    conn.execute(
                        delete(rate_limit_table).where(
                            rate_limit_table.c.timestamp <= window_start
                        )
                    )

                # Count requests within the current window for this key
                count = conn.execute(
                    select(func.count()).select_from(rate_limit_table).where(
                        rate_limit_table.c.key == key,
                        rate_limit_table.c.timestamp > window_start,
                    )
                ).scalar()

                if count >= self.max_requests:
                    return False

                # Insert new timestamp
                conn.execute(
                    insert(rate_limit_table).values(key=key, timestamp=now)
                )
                return True

        except Exception as exc:
            # Fail open: if database is unavailable, allow the request
            logger.warning("Rate limit DB check failed, allowing request: %s", exc)
            return True

    # ------------------------------------------------------------------
    # File backend implementation (JSON backend, unchanged)
    # ------------------------------------------------------------------

    def _is_allowed_file(self, key: str) -> bool:
        """Check rate limit using file-based storage with fcntl locks."""
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
            with open(self.storage_path, encoding="utf-8") as f:
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
