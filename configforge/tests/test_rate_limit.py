"""Tests for the RateLimiter utility."""

import json
import os
import time
import pytest

from configforge.utils.rate_limit import RateLimiter


@pytest.fixture
def limiter(tmp_path):
    """Create a RateLimiter with a temp storage file."""
    storage = str(tmp_path / "rate_limit.json")
    return RateLimiter(max_requests=3, window_seconds=60, storage_path=storage)


class TestIsAllowed:
    def test_is_allowed_normal_request(self, limiter):
        """Normal requests within limit should be allowed."""
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

    def test_is_allowed_exceeds_limit(self, limiter):
        """Requests exceeding the limit should be denied."""
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        # 4th request should be denied
        assert limiter.is_allowed("user1") is False

    def test_is_allowed_independent_keys(self, limiter):
        """Different keys should have independent rate limits."""
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        # user1 is at limit, but user2 should still be allowed
        assert limiter.is_allowed("user2") is True

    def test_is_allowed_single_request(self, tmp_path):
        """RateLimiter with max_requests=1 should allow only one request."""
        limiter = RateLimiter(max_requests=1, window_seconds=60, storage_path=str(tmp_path / "rl1.json"))
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False

    def test_is_allowed_returns_false_then_true_after_window(self, tmp_path):
        """After the window expires, requests should be allowed again."""
        storage = str(tmp_path / "rl_window.json")
        limiter = RateLimiter(max_requests=1, window_seconds=1, storage_path=storage)
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False
        time.sleep(1.1)
        assert limiter.is_allowed("key1") is True
        # cleanup
        if os.path.exists(storage):
            os.remove(storage)


class TestCleanupExpired:
    def test_cleanup_expired_removes_old_entries(self, limiter):
        """Expired timestamps should be cleaned up."""
        # Manually inject old timestamps
        state = {"user1": [time.time() - 120, time.time() - 100]}
        cleaned = limiter._cleanup_expired(state)
        assert "user1" not in cleaned

    def test_cleanup_expired_keeps_recent_entries(self, limiter):
        """Recent timestamps should be kept."""
        now = time.time()
        state = {"user1": [now - 10, now - 5]}
        cleaned = limiter._cleanup_expired(state)
        assert "user1" in cleaned
        assert len(cleaned["user1"]) == 2

    def test_cleanup_expired_removes_keys_with_no_timestamps(self, limiter):
        """Keys with only expired timestamps should be removed entirely."""
        state = {"user1": [time.time() - 200], "user2": [time.time() - 10]}
        cleaned = limiter._cleanup_expired(state)
        assert "user1" not in cleaned
        assert "user2" in cleaned

    def test_cleanup_on_is_allowed(self, limiter):
        """is_allowed should clean up expired entries as a side effect."""
        # Use up the limit
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False

        # Manually write expired timestamps
        state = {"user1": [time.time() - 120]}
        limiter._save_state(state)

        # Now is_allowed should clean up and allow the request
        assert limiter.is_allowed("user1") is True


class TestFilePersistence:
    def test_state_persisted_to_file(self, limiter):
        """State should be persisted to the JSON file."""
        limiter.is_allowed("user1")
        assert os.path.exists(limiter.storage_path)
        with open(limiter.storage_path, "r") as f:
            state = json.load(f)
        assert "user1" in state
        assert len(state["user1"]) == 1

    def test_state_loaded_from_file(self, limiter):
        """State should be loaded from the JSON file on subsequent calls."""
        limiter.is_allowed("user1")
        # Create a new limiter instance with the same storage path
        limiter2 = RateLimiter(
            max_requests=3, window_seconds=60, storage_path=limiter.storage_path
        )
        # The new limiter should see the existing state
        state = limiter2._load_state()
        assert "user1" in state

    def test_load_state_handles_missing_file(self, tmp_path):
        """_load_state should return empty dict when file doesn't exist."""
        limiter = RateLimiter(storage_path=str(tmp_path / "nonexistent.json"))
        state = limiter._load_state()
        assert state == {}

    def test_load_state_handles_corrupt_file(self, limiter):
        """_load_state should return empty dict for corrupt JSON."""
        os.makedirs(os.path.dirname(limiter.storage_path), exist_ok=True)
        with open(limiter.storage_path, "w") as f:
            f.write("not valid json")
        state = limiter._load_state()
        assert state == {}

    def test_save_creates_directory(self, tmp_path):
        """_save_state should create the parent directory if needed."""
        storage = str(tmp_path / "subdir" / "rate_limit.json")
        limiter = RateLimiter(storage_path=storage)
        limiter._save_state({"key": [1.0]})
        assert os.path.exists(storage)
