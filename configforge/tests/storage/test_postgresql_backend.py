"""PostgreSQL 后端集成测试 (T-5E-03)。

验证通用 SQL 后端在 PostgreSQL 上的功能完整性。
需要真实 PostgreSQL 实例，通过环境变量 CONFIGFORGE_TEST_POSTGRES_URL 配置。

运行方式：
    # 跳过（默认，无 PostgreSQL 环境）
    pytest configforge/tests/storage/test_postgresql_backend.py

    # 启用（需先启动 PostgreSQL）
    export CONFIGFORGE_TEST_POSTGRES_URL="postgresql://user:pass@localhost:5432/configforge_test"
    pytest configforge/tests/storage/test_postgresql_backend.py -v

测试覆盖：
- 引擎创建与 schema 初始化
- 6 个 Store 的核心 CRUD（ConnectionStore / TemplateStore / UserStore / AuditStore / SettingsStore / ScheduleStore）
- 加密字段（Fernet）跨后端兼容
- 方言无关性验证（Integer 表示布尔值）
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Skip 条件：无 CONFIGFORGE_TEST_POSTGRES_URL 时跳过所有测试
# ---------------------------------------------------------------------------

_POSTGRES_URL = os.environ.get("CONFIGFORGE_TEST_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not _POSTGRES_URL,
    reason="PostgreSQL integration tests require CONFIGFORGE_TEST_POSTGRES_URL env var",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def postgres_engine():
    """创建独立的 PostgreSQL 测试数据库（每个测试模块一个 database）。

    策略：连接到 CONFIGFORGE_TEST_POSTGRES_URL 指定的数据库，
    测试开始前 DROP 所有表，测试结束后 DROP 所有表。
    避免与生产数据冲突。
    """
    from configforge.storage.sql_schema import get_engine, init_schema, metadata

    # 保存原始环境变量，确保模块结束后恢复（避免污染其他测试模块）
    orig_backend = os.environ.get("CONFIGFORGE_STORAGE_BACKEND")
    orig_db_url = os.environ.get("CONFIGFORGE_DATABASE_URL")

    # 清除 get_engine 的 lru_cache，确保使用新的环境变量
    get_engine.cache_clear()

    # 设置环境变量
    os.environ["CONFIGFORGE_STORAGE_BACKEND"] = "postgresql"
    os.environ["CONFIGFORGE_DATABASE_URL"] = _POSTGRES_URL

    engine = get_engine()

    # 测试前：DROP 并重建所有表
    with engine.connect() as conn:
        # Disable foreign key checks during cleanup
        conn.execute(text("SET session_replication_role = 'replica'"))
        conn.commit()
    metadata.drop_all(engine)
    init_schema(engine)

    yield engine

    # 测试后：清空所有表
    with engine.connect() as conn:
        conn.execute(text("SET session_replication_role = 'replica'"))
        metadata.drop_all(engine)
        conn.execute(text("SET session_replication_role = 'origin'"))
        conn.commit()
    engine.dispose()
    get_engine.cache_clear()

    # 清除工厂函数 lru_cache，避免缓存 PostgreSQL store 实例污染后续测试
    from configforge.storage import (
        get_audit_store,
        get_connection_store,
        get_schedule_store,
        get_template_store,
        get_user_store,
    )
    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()

    # 恢复原始环境变量，避免污染后续测试模块
    if orig_backend is None:
        os.environ.pop("CONFIGFORGE_STORAGE_BACKEND", None)
    else:
        os.environ["CONFIGFORGE_STORAGE_BACKEND"] = orig_backend
    if orig_db_url is None:
        os.environ.pop("CONFIGFORGE_DATABASE_URL", None)
    else:
        os.environ["CONFIGFORGE_DATABASE_URL"] = orig_db_url


@pytest.fixture(autouse=True)
def clear_tables(postgres_engine):
    """每个测试前清空所有表数据（不 DROP，只 DELETE）。"""
    from sqlalchemy import delete

    from configforge.storage.sql_schema import (
        audit_log_table,
        connections_table,
        schedules_table,
        settings_table,
        templates_table,
        users_table,
    )

    with postgres_engine.begin() as conn:
        # Disable FK checks, delete all, re-enable
        conn.execute(text("SET session_replication_role = 'replica'"))
        conn.execute(delete(audit_log_table))
        conn.execute(delete(schedules_table))
        conn.execute(delete(settings_table))
        conn.execute(delete(templates_table))
        conn.execute(delete(users_table))
        conn.execute(delete(connections_table))
        conn.execute(text("SET session_replication_role = 'origin'"))


@pytest.fixture
def postgres_env(postgres_engine, tmp_path, monkeypatch):
    """配置 PostgreSQL 后端环境变量。"""
    monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "postgresql")
    monkeypatch.setenv("CONFIGFORGE_DATABASE_URL", _POSTGRES_URL)
    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path))

    from configforge.storage import (
        get_audit_store,
        get_connection_store,
        get_schedule_store,
        get_template_store,
        get_user_store,
    )
    from configforge.storage.sql_schema import get_engine

    get_engine.cache_clear()
    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()

    yield {"url": _POSTGRES_URL}

    get_engine.cache_clear()
    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()


# ---------------------------------------------------------------------------
# Engine & Schema Tests
# ---------------------------------------------------------------------------


class TestPostgresEngine:
    """PostgreSQL 引擎与 schema 初始化。"""

    def test_engine_url_is_postgresql(self, postgres_env):
        from configforge.storage.sql_schema import get_database_url
        url = get_database_url()
        assert url.startswith("postgresql"), f"Expected postgresql URL, got: {url}"

    def test_engine_dialect_is_postgresql(self, postgres_engine):
        dialect = postgres_engine.dialect.name
        assert dialect == "postgresql", f"Expected postgresql dialect, got: {dialect}"

    def test_all_tables_created(self, postgres_engine):
        """6 张表应全部创建。"""
        from configforge.storage.sql_schema import metadata
        with postgres_engine.connect() as conn:
            existing = set()
            for table_name in metadata.tables:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = :name)"
                    ),
                    {"name": table_name},
                )
                if result.scalar():
                    existing.add(table_name)
        expected = set(metadata.tables.keys())
        assert expected == existing, f"Missing tables: {expected - existing}"


# ---------------------------------------------------------------------------
# ConnectionStore Tests
# ---------------------------------------------------------------------------


class TestPostgresConnectionStore:
    """PostgreSQL ConnectionStore CRUD。"""

    def test_create_and_get_mysql_connection(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        created = store.create({
            "name": "test-mysql",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "username": "root",
            "password": "secret",
        })
        assert created["name"] == "test-mysql"
        assert created["db_type"] == "mysql"
        assert created["passwordSet"] is True
        assert created["verified"] is False

        # GET returns summary
        fetched = store.get(created["id"])
        assert fetched is not None
        assert fetched["name"] == "test-mysql"
        assert fetched["host"] == "localhost"

    def test_create_sqlite_connection(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        created = store.create({
            "name": "test-sqlite",
            "db_type": "sqlite",
            "file_path": "/tmp/test.db",
        })
        assert created["db_type"] == "sqlite"
        assert created["host"] == "/tmp/test.db"
        assert "port" not in created

    def test_password_is_encrypted_in_db(self, postgres_env):
        """明文密码不应直接存入数据库，应 Fernet 加密。"""
        from sqlalchemy import select

        from configforge.storage.sql_backend import SqliteConnectionStore
        from configforge.storage.sql_schema import connections_table, get_engine

        store = SqliteConnectionStore()
        store.create({
            "name": "enc-test",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "db",
            "username": "u",
            "password": "my-secret-password",
        })

        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                select(connections_table.c.password).where(
                    connections_table.c.name == "enc-test"
                )
            ).fetchone()
        assert row is not None
        stored_password = row[0]
        assert stored_password != "my-secret-password"
        assert len(stored_password) > 20  # Fernet tokens are long

    def test_get_with_plaintext_password(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        created = store.create({
            "name": "plain-test",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "db",
            "username": "u",
            "password": "decrypted-secret",
        })
        entry = store.get_with_plaintext_password(created["id"])
        assert entry is not None
        assert entry["password"] == "decrypted-secret"

    def test_update_connection(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        created = store.create({
            "name": "update-test",
            "db_type": "mysql",
            "host": "old-host",
            "port": 3306,
            "database": "db",
            "username": "u",
            "password": "p",
        })
        updated = store.update(created["id"], {"name": "updated-name", "host": "new-host"})
        assert updated is not None
        assert updated["name"] == "updated-name"
        assert updated["host"] == "new-host"

    def test_delete_connection(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        created = store.create({
            "name": "delete-test",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "db",
            "username": "u",
            "password": "p",
        })
        assert store.delete(created["id"]) is True
        assert store.get(created["id"]) is None

    def test_list_all(self, postgres_env):
        from configforge.storage.sql_backend import SqliteConnectionStore
        store = SqliteConnectionStore()

        store.create({"name": "c1", "db_type": "sqlite", "file_path": "/tmp/1.db"})
        store.create({"name": "c2", "db_type": "sqlite", "file_path": "/tmp/2.db"})
        all_conns = store.list_all()
        assert len(all_conns) == 2


# ---------------------------------------------------------------------------
# TemplateStore Tests
# ---------------------------------------------------------------------------


class TestPostgresTemplateStore:
    """PostgreSQL TemplateStore CRUD。"""

    def test_create_and_get_template(self, postgres_env):
        from configforge.storage.sql_backend import SqliteTemplateStore
        store = SqliteTemplateStore()

        created = store.create_template(
            name="test-template",
            description="A test template",
            category="mysql",
            tags=["test", "mysql"],
            config_state={"version": "1.0", "nodes": []},
            author="tester",
        )
        assert created["name"] == "test-template"
        assert created["tags"] == ["test", "mysql"]
        assert created["config_state"] == {"version": "1.0", "nodes": []}

        fetched = store.get_template(created["id"])
        assert fetched is not None
        assert fetched["name"] == "test-template"

    def test_list_and_search(self, postgres_env):
        from configforge.storage.sql_backend import SqliteTemplateStore
        store = SqliteTemplateStore()

        store.create_template("MySQL Backup", "backup config", "mysql", ["backup"], {})
        store.create_template("Redis Cache", "cache config", "redis", ["cache"], {})

        all_templates = store.list_templates()
        assert len(all_templates) == 2

        mysql_only = store.list_templates(category="mysql")
        assert len(mysql_only) == 1
        assert mysql_only[0]["name"] == "MySQL Backup"

        search_results = store.list_templates(search="cache")
        assert len(search_results) == 1
        assert search_results[0]["name"] == "Redis Cache"

    def test_update_template(self, postgres_env):
        from configforge.storage.sql_backend import SqliteTemplateStore
        store = SqliteTemplateStore()

        created = store.create_template("old-name", "desc", "mysql", [], {})
        updated = store.update_template(created["id"], name="new-name", version="2.0")
        assert updated is not None
        assert updated["name"] == "new-name"
        assert updated["version"] == "2.0"

    def test_increment_usage(self, postgres_env):
        from configforge.storage.sql_backend import SqliteTemplateStore
        store = SqliteTemplateStore()

        created = store.create_template("usage-test", "", "mysql", [], {})
        store.increment_usage(created["id"])
        store.increment_usage(created["id"])
        fetched = store.get_template(created["id"])
        assert fetched["usage_count"] == 2

    def test_delete_template(self, postgres_env):
        from configforge.storage.sql_backend import SqliteTemplateStore
        store = SqliteTemplateStore()

        created = store.create_template("delete-test", "", "mysql", [], {})
        assert store.delete_template(created["id"]) is True
        assert store.get_template(created["id"]) is None


# ---------------------------------------------------------------------------
# UserStore Tests
# ---------------------------------------------------------------------------


class TestPostgresUserStore:
    """PostgreSQL UserStore CRUD + 密码哈希。"""

    def test_create_and_authenticate(self, postgres_env):
        from configforge.storage.sql_backend import SqliteUserStore
        store = SqliteUserStore()

        user = store.create_user("testuser", "password123", "editor")
        assert user is not None
        assert user.username == "testuser"
        assert user.role == "editor"

        # Correct password
        authed = store.authenticate("testuser", "password123")
        assert authed is not None
        assert authed.username == "testuser"

        # Wrong password
        assert store.authenticate("testuser", "wrong") is None

    def test_duplicate_username_rejected(self, postgres_env):
        from configforge.storage.sql_backend import SqliteUserStore
        store = SqliteUserStore()

        store.create_user("dup", "pass1", "editor")
        result = store.create_user("dup", "pass2", "editor")
        assert result is None

    def test_list_and_delete(self, postgres_env):
        from configforge.storage.sql_backend import SqliteUserStore
        store = SqliteUserStore()

        u1 = store.create_user("user1", "p1", "editor")
        store.create_user("user2", "p2", "editor")
        assert len(store.list_users()) == 2

        assert store.delete_user(u1.id) is True
        assert len(store.list_users()) == 1

    def test_change_password(self, postgres_env):
        from configforge.storage.sql_backend import SqliteUserStore
        store = SqliteUserStore()

        user = store.create_user("pwduser", "old-pass", "editor")
        assert store.change_password(user.id, "old-pass", "new-pass") is True
        assert store.authenticate("pwduser", "new-pass") is not None
        assert store.authenticate("pwduser", "old-pass") is None

    def test_ensure_default_admin(self, postgres_env):
        from configforge.storage.sql_backend import SqliteUserStore
        store = SqliteUserStore()

        store.ensure_default_admin()
        admin = store.authenticate("admin", "admin123")
        assert admin is not None
        assert admin.role == "admin"

        # Idempotent: second call should not fail or create duplicate
        store.ensure_default_admin()
        admins = [u for u in store.list_users() if u.username == "admin"]
        assert len(admins) == 1


# ---------------------------------------------------------------------------
# AuditStore Tests
# ---------------------------------------------------------------------------


class TestPostgresAuditStore:
    """PostgreSQL AuditStore CRUD + 修剪。"""

    def test_log_and_get_audit(self, postgres_env):
        from configforge.storage.sql_backend import SqliteAuditStore
        store = SqliteAuditStore()

        store.log_audit("create", "connection", "conn-1", {"user": "admin"})
        store.log_audit("delete", "template", "tmpl-1", {"user": "editor"})

        entries = store.get_audit_log()
        assert len(entries) == 2
        # Chronological order (oldest first)
        assert entries[0]["action"] == "create"
        assert entries[1]["action"] == "delete"

    def test_filter_by_target_type(self, postgres_env):
        from configforge.storage.sql_backend import SqliteAuditStore
        store = SqliteAuditStore()

        store.log_audit("create", "connection", "c1", {})
        store.log_audit("create", "template", "t1", {})

        conn_entries = store.get_audit_log(target_type="connection")
        assert len(conn_entries) == 1
        assert conn_entries[0]["target_id"] == "c1"

    def test_filter_by_action(self, postgres_env):
        from configforge.storage.sql_backend import SqliteAuditStore
        store = SqliteAuditStore()

        store.log_audit("create", "connection", "c1", {})
        store.log_audit("delete", "connection", "c2", {})

        delete_entries = store.get_audit_log(action="delete")
        assert len(delete_entries) == 1
        assert delete_entries[0]["target_id"] == "c2"


# ---------------------------------------------------------------------------
# SettingsStore Tests
# ---------------------------------------------------------------------------


class TestPostgresSettingsStore:
    """PostgreSQL SettingsStore CRUD + 加密。"""

    def test_smtp_settings_save_and_load(self, postgres_env):
        from configforge.services.notifier.smtp_settings import SmtpSettings
        from configforge.storage.sql_backend import SqliteSettingsStore
        store = SqliteSettingsStore(kind="smtp")

        # Default when empty
        default = store.load_settings()
        assert isinstance(default, SmtpSettings)

        # Save and reload
        settings = SmtpSettings(
            host="smtp.test.com",
            port=587,
            user="user@test.com",
            password="smtp-secret",
            sender="noreply@test.com",
        )
        store.save_settings(settings)

        loaded = store.load_settings()
        assert loaded.host == "smtp.test.com"
        assert loaded.port == 587
        assert loaded.password == "smtp-secret"  # Decrypted

    def test_ai_settings_save_and_load(self, postgres_env):
        from configforge.models.ai import AiSettings
        from configforge.storage.sql_backend import SqliteSettingsStore
        store = SqliteSettingsStore(kind="ai")

        settings = AiSettings(
            provider="openai",
            api_key="sk-test-key-123",
            model="gpt-4",
        )
        store.save_settings(settings)

        loaded = store.load_settings()
        assert loaded.provider == "openai"
        assert loaded.api_key == "sk-test-key-123"  # Decrypted
        assert loaded.model == "gpt-4"

    def test_password_is_encrypted_in_db(self, postgres_env):
        """SMTP 密码在数据库中应 Fernet 加密。"""
        import json

        from sqlalchemy import select

        from configforge.services.notifier.smtp_settings import SmtpSettings
        from configforge.storage.sql_backend import SqliteSettingsStore
        from configforge.storage.sql_schema import get_engine, settings_table

        store = SqliteSettingsStore(kind="smtp")
        store.save_settings(SmtpSettings(
            host="h", port=587, user="u", password="secret-in-db", sender="e@t.com"
        ))

        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                select(settings_table.c.data).where(settings_table.c.kind == "smtp")
            ).fetchone()
        data = json.loads(row[0])
        assert data["password"] != "secret-in-db"
        assert len(data["password"]) > 20


# ---------------------------------------------------------------------------
# ScheduleStore Tests
# ---------------------------------------------------------------------------


class TestPostgresScheduleStore:
    """PostgreSQL ScheduleStore CRUD。"""

    def test_add_and_list_schedule(self, postgres_env):
        from configforge.storage.sql_backend import SqliteScheduleStore
        store = SqliteScheduleStore()

        sched = store.add_schedule({
            "config_id": "config-1",
            "cron_expression": "0 2 * * *",
            "description": "Daily backup",
        })
        assert sched["config_id"] == "config-1"
        assert sched["cron_expression"] == "0 2 * * *"
        assert sched["enabled"] is True

        all_scheds = store.list_schedules()
        assert len(all_scheds) == 1

    def test_update_schedule(self, postgres_env):
        from configforge.storage.sql_backend import SqliteScheduleStore
        store = SqliteScheduleStore()

        sched = store.add_schedule({
            "config_id": "c1",
            "cron_expression": "0 2 * * *",
            "description": "old",
        })
        updated = store.update_schedule(sched["id"], description="new desc")
        assert updated is not None
        assert updated["description"] == "new desc"

    def test_toggle_schedule(self, postgres_env):
        from configforge.storage.sql_backend import SqliteScheduleStore
        store = SqliteScheduleStore()

        sched = store.add_schedule({
            "config_id": "c1",
            "cron_expression": "0 2 * * *",
        })
        assert sched["enabled"] is True

        toggled = store.toggle_schedule(sched["id"])
        assert toggled["enabled"] is False

        toggled_again = store.toggle_schedule(sched["id"])
        assert toggled_again["enabled"] is True

    def test_remove_schedule(self, postgres_env):
        from configforge.storage.sql_backend import SqliteScheduleStore
        store = SqliteScheduleStore()

        sched = store.add_schedule({
            "config_id": "c1",
            "cron_expression": "0 2 * * *",
        })
        assert store.remove_schedule(sched["id"]) is True
        assert len(store.list_schedules()) == 0

    def test_invalid_cron_rejected(self, postgres_env):
        from configforge.storage.sql_backend import SqliteScheduleStore
        store = SqliteScheduleStore()

        with pytest.raises(Exception):
            store.add_schedule({
                "config_id": "c1",
                "cron_expression": "invalid-cron",
            })
