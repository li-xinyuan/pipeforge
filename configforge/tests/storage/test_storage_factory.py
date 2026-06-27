"""存储工厂函数测试 (T-5E-01 / T-5E-02)。

验证：
- 后端切换通过环境变量 CONFIGFORGE_STORAGE_BACKEND 控制
- 工厂函数返回正确的 Store 实例
- 大小写不敏感
- 未实现的后端抛出 NotImplementedError
- 所有 Store 实例满足对应 Protocol
"""
from __future__ import annotations

import pytest

from configforge.storage import (
    get_audit_store,
    get_connection_store,
    get_schedule_store,
    get_settings_store,
    get_template_store,
    get_user_store,
)
from configforge.storage.base import (
    AuditStoreProtocol,
    ConnectionStoreProtocol,
    ScheduleStoreProtocol,
    SettingsStoreProtocol,
    TemplateStoreProtocol,
    UserStoreProtocol,
)
from configforge.storage.json_backend import (
    JsonAuditStore,
    JsonConnectionStore,
    JsonScheduleStore,
    JsonSettingsStore,
    JsonTemplateStore,
    JsonUserStore,
)


class TestFactoryJsonBackend:
    """JSON 后端（默认）工厂函数。"""

    def test_get_connection_store_returns_json(self, json_env):
        store = get_connection_store()
        assert isinstance(store, JsonConnectionStore)

    def test_get_template_store_returns_json(self, json_env):
        store = get_template_store()
        assert isinstance(store, JsonTemplateStore)

    def test_get_user_store_returns_json(self, json_env):
        store = get_user_store()
        assert isinstance(store, JsonUserStore)

    def test_get_audit_store_returns_json(self, json_env):
        store = get_audit_store()
        assert isinstance(store, JsonAuditStore)

    def test_get_schedule_store_returns_json(self, json_env):
        store = get_schedule_store()
        assert isinstance(store, JsonScheduleStore)

    def test_get_settings_store_smtp_returns_json(self, json_env):
        store = get_settings_store(kind="smtp")
        assert isinstance(store, JsonSettingsStore)

    def test_get_settings_store_ai_returns_json(self, json_env):
        store = get_settings_store(kind="ai")
        assert isinstance(store, JsonSettingsStore)


class TestFactorySqliteBackend:
    """SQLite 后端工厂函数。"""

    def test_get_connection_store_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteConnectionStore
        store = get_connection_store()
        assert isinstance(store, SqliteConnectionStore)

    def test_get_template_store_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteTemplateStore
        store = get_template_store()
        assert isinstance(store, SqliteTemplateStore)

    def test_get_user_store_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteUserStore
        store = get_user_store()
        assert isinstance(store, SqliteUserStore)

    def test_get_audit_store_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteAuditStore
        store = get_audit_store()
        assert isinstance(store, SqliteAuditStore)

    def test_get_schedule_store_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteScheduleStore
        store = get_schedule_store()
        assert isinstance(store, SqliteScheduleStore)

    def test_get_settings_store_smtp_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteSettingsStore
        store = get_settings_store(kind="smtp")
        assert isinstance(store, SqliteSettingsStore)
        assert store._kind == "smtp"

    def test_get_settings_store_ai_returns_sqlite(self, sqlite_env):
        from configforge.storage.sqlite_backend import SqliteSettingsStore
        store = get_settings_store(kind="ai")
        assert isinstance(store, SqliteSettingsStore)
        assert store._kind == "ai"


class TestProtocolCompliance:
    """所有 Store 实例应满足对应 Protocol（@runtime_checkable）。"""

    def test_json_stores_satisfy_protocols(self, json_env):
        assert isinstance(get_connection_store(), ConnectionStoreProtocol)
        assert isinstance(get_template_store(), TemplateStoreProtocol)
        assert isinstance(get_user_store(), UserStoreProtocol)
        assert isinstance(get_audit_store(), AuditStoreProtocol)
        assert isinstance(get_schedule_store(), ScheduleStoreProtocol)
        assert isinstance(get_settings_store("smtp"), SettingsStoreProtocol)

    def test_sqlite_stores_satisfy_protocols(self, sqlite_env):
        assert isinstance(get_connection_store(), ConnectionStoreProtocol)
        assert isinstance(get_template_store(), TemplateStoreProtocol)
        assert isinstance(get_user_store(), UserStoreProtocol)
        assert isinstance(get_audit_store(), AuditStoreProtocol)
        assert isinstance(get_schedule_store(), ScheduleStoreProtocol)
        assert isinstance(get_settings_store("ai"), SettingsStoreProtocol)


class TestBackendNotImplemented:
    """未实现的后端应抛出 NotImplementedError。"""

    def test_postgresql_without_url_raises_runtime_error(self, tmp_path, monkeypatch):
        """PostgreSQL 后端已实现（T-5E-03），但缺少 CONFIGFORGE_DATABASE_URL 应抛 RuntimeError。"""
        monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "postgresql")
        monkeypatch.delenv("CONFIGFORGE_DATABASE_URL", raising=False)
        # Clear cache
        get_connection_store.cache_clear()
        try:
            with pytest.raises(RuntimeError, match="CONFIGFORGE_DATABASE_URL"):
                get_connection_store()
        finally:
            get_connection_store.cache_clear()

    def test_mongodb_raises_not_implemented(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "mongodb")
        get_template_store.cache_clear()
        try:
            with pytest.raises(NotImplementedError, match="mongodb"):
                get_template_store()
        finally:
            get_template_store.cache_clear()


class TestCaseInsensitiveBackend:
    """后端名称应大小写不敏感。"""

    def test_uppercase_SQLITE(self, tmp_path, monkeypatch):
        from configforge.storage.sqlite_backend import SqliteConnectionStore
        monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "SQLITE")
        monkeypatch.setenv("CONFIGFORGE_SQLITE_PATH", str(tmp_path / "test.db"))
        from configforge.storage.sqlite_schema import get_engine
        get_engine.cache_clear()
        get_connection_store.cache_clear()
        try:
            store = get_connection_store()
            assert isinstance(store, SqliteConnectionStore)
        finally:
            get_engine.cache_clear()
            get_connection_store.cache_clear()

    def test_mixed_case_Sqlite(self, tmp_path, monkeypatch):
        from configforge.storage.sqlite_backend import SqliteTemplateStore
        monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "Sqlite")
        monkeypatch.setenv("CONFIGFORGE_SQLITE_PATH", str(tmp_path / "test.db"))
        from configforge.storage.sqlite_schema import get_engine
        get_engine.cache_clear()
        get_template_store.cache_clear()
        try:
            store = get_template_store()
            assert isinstance(store, SqliteTemplateStore)
        finally:
            get_engine.cache_clear()
            get_template_store.cache_clear()


class TestFactoryCaching:
    """工厂函数应缓存单例（lru_cache）。"""

    def test_connection_store_cached(self, json_env):
        s1 = get_connection_store()
        s2 = get_connection_store()
        assert s1 is s2

    def test_template_store_cached(self, json_env):
        s1 = get_template_store()
        s2 = get_template_store()
        assert s1 is s2

    def test_settings_store_not_cached(self, json_env):
        """get_settings_store 因 kind 参数不缓存。"""
        s1 = get_settings_store("smtp")
        s2 = get_settings_store("smtp")
        # Different instances (not cached)
        assert s1 is not s2
