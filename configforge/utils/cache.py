"""Simple TTL memory cache for ConfigForge stores."""

import threading
import time


class TTLCache:
    """Thread-safe time-to-live cache.

    Args:
        ttl: Time-to-live in seconds. Cached entries expire after this duration.
    """

    def __init__(self, ttl: float = 30.0):
        self._cache: dict[str, tuple[float, object]] = {}
        self._ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str):
        """Get a cached value. Returns None if not found or expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.monotonic() - ts < self._ttl:
                return data
            # Expired — remove and return None
            del self._cache[key]
            return None

    def set(self, key: str, data):
        """Store a value in the cache."""
        with self._lock:
            self._cache[key] = (time.monotonic(), data)

    def invalidate(self, key: str | None = None):
        """Invalidate a specific key, or all keys if key is None."""
        with self._lock:
            if key is None:
                self._cache.clear()
            else:
                self._cache.pop(key, None)

    def invalidate_pattern(self, prefix: str):
        """Invalidate all keys starting with prefix."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
