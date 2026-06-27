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
        with open(limiter.storage_path) as f:
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


# ---------------------------------------------------------------------------
# T-5E-04: SQL 后端限流测试 — 跨实例共享状态
# ---------------------------------------------------------------------------


@pytest.fixture
def sql_limiter_env(tmp_path, monkeypatch):
    """T-5E-04: 配置 SQL 后端环境用于限流测试。

    使用独立临时 SQLite 数据库，避免与其他测试污染。
    清理 lru_cache 确保新环境变量被 get_engine() 读取。
    """
    data_dir = str(tmp_path / "data")
    db_path = str(tmp_path / "test_rate_limit.db")
    os.makedirs(data_dir, exist_ok=True)

    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", data_dir)
    monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("CONFIGFORGE_SQLITE_PATH", db_path)

    from configforge.storage.sqlite_schema import get_engine
    get_engine.cache_clear()

    yield {"data_dir": data_dir, "db_path": db_path}

    get_engine.cache_clear()
    # 清理 WAL/SHM 文件（SQLite WAL 模式产生的附属文件）
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


class TestSqlBackend:
    """T-5E-04: SQL 后端限流测试 — 验证跨实例共享状态。

    SQL 后端（SQLite/PostgreSQL）将限流状态存储在数据库中，
    多个 RateLimiter 实例（模拟多主机）共享同一数据库时，
    限流计数应跨实例聚合。
    """

    def test_sql_backend_basic_allow(self, sql_limiter_env):
        """SQL 后端：限制内的请求应允许。"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

    def test_sql_backend_exceeds_limit(self, sql_limiter_env):
        """SQL 后端：超出限制的请求应拒绝。"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        # 第 3 次应被拒绝
        assert limiter.is_allowed("user1") is False

    def test_sql_backend_independent_keys(self, sql_limiter_env):
        """SQL 后端：不同 key 的限流应相互独立。"""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("user1") is True
        # user1 已达上限，但 user2 应允许
        assert limiter.is_allowed("user2") is True
        # user1 应被拒绝
        assert limiter.is_allowed("user1") is False

    def test_sql_backend_window_expiry(self, sql_limiter_env):
        """SQL 后端：窗口过期后应重新允许请求。"""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False
        time.sleep(1.1)
        assert limiter.is_allowed("key1") is True

    def test_sql_backend_cross_instance_shared_state(self, sql_limiter_env):
        """T-5E-04 核心：两个 RateLimiter 实例共享同一数据库，
        跨实例限流应生效（模拟多主机部署）。

        场景：host A 和 host B 连接同一数据库。
        host A 消耗完配额后，host B 应看到聚合计数并拒绝请求。
        """
        # 实例 1（模拟 host A）
        limiter_a = RateLimiter(max_requests=2, window_seconds=60)
        # 实例 2（模拟 host B）—— 同一数据库
        limiter_b = RateLimiter(max_requests=2, window_seconds=60)

        # host A 消耗 2 次配额
        assert limiter_a.is_allowed("shared_key") is True
        assert limiter_a.is_allowed("shared_key") is True

        # host B 应看到 host A 的计数并拒绝
        assert limiter_b.is_allowed("shared_key") is False

    def test_sql_backend_fail_open_on_db_error(self, sql_limiter_env, monkeypatch):
        """SQL 后端：数据库异常时应 fail-open（允许请求通过）。

        可用性优先：限流失败不应阻断正常请求。
        """
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # 强制 get_engine 抛异常
        def _raise(*args, **kwargs):
            raise RuntimeError("DB unavailable")

        monkeypatch.setattr(
            "configforge.storage.sql_schema.get_engine", _raise
        )
        # 不应抛异常，应返回 True（fail-open）
        assert limiter.is_allowed("user1") is True

    def test_sql_backend_cleanup_expired_entries(self, sql_limiter_env):
        """SQL 后端：is_allowed 应清理该 key 的过期限流条目。"""
        from sqlalchemy import func, insert, select

        from configforge.storage.sql_schema import get_engine, rate_limit_table

        limiter = RateLimiter(max_requests=1, window_seconds=1)

        # 手动插入一个过期条目
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                insert(rate_limit_table).values(
                    key="old_key", timestamp=time.time() - 100
                )
            )

        # is_allowed 应清理过期条目并允许新请求
        assert limiter.is_allowed("old_key") is True

        # 验证：过期条目被清理，只剩 is_allowed 插入的新条目
        with engine.connect() as conn:
            count = conn.execute(
                select(func.count()).select_from(rate_limit_table).where(
                    rate_limit_table.c.key == "old_key"
                )
            ).scalar()
        assert count == 1

    def test_sql_backend_records_timestamp(self, sql_limiter_env):
        """SQL 后端：is_allowed=True 应在数据库插入新条目。"""
        from sqlalchemy import func, select

        from configforge.storage.sql_schema import get_engine, rate_limit_table

        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.is_allowed("tracked_key") is True

        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                select(func.count()).select_from(rate_limit_table).where(
                    rate_limit_table.c.key == "tracked_key"
                )
            ).scalar()
        assert count == 1
