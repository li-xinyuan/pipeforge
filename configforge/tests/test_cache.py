"""Tests for TTLCache."""
import time

from configforge.utils.cache import TTLCache


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(ttl=10.0)
        cache.set("key", {"data": 1})
        assert cache.get("key") == {"data": 1}

    def test_get_missing_key(self):
        cache = TTLCache(ttl=10.0)
        assert cache.get("nonexistent") is None

    def test_expired_entry(self):
        cache = TTLCache(ttl=0.1)
        cache.set("key", "value")
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_invalidate_specific_key(self):
        cache = TTLCache(ttl=10.0)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_invalidate_all(self):
        cache = TTLCache(ttl=10.0)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite(self):
        cache = TTLCache(ttl=10.0)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"
