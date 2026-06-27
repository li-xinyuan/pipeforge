"""SQLite 后端 Store 单测 (T-5E-02)。

覆盖 6 个 Sqlite*Store 的核心 CRUD、加密字段、JSON 序列化、
密码哈希、审计日志修剪、Settings 加解密、Schedule cron 验证。
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from configforge.storage.sqlite_backend import (
    SqliteAuditStore,
    SqliteConnectionStore,
    SqliteScheduleStore,
    SqliteSettingsStore,
    SqliteTemplateStore,
    SqliteUserStore,
)
from configforge.storage.sqlite_schema import (
    connections_table,
    get_engine,
    settings_table,
    users_table,
)

# ---------------------------------------------------------------------------
# SqliteConnectionStore
# ---------------------------------------------------------------------------


class TestSqliteConnectionStore:
    """ConnectionStore — CRUD + Fernet 加密 + 摘要格式。"""

    def test_create_mysql_connection_returns_summary(self, sqlite_env):
        store = SqliteConnectionStore()
        conn = store.create({
            "name": "Test MySQL", "db_type": "mysql",
            "host": "localhost", "port": 3306, "database": "testdb",
            "username": "root", "password": "secret123",
        })
        # Summary fields
        assert conn["name"] == "Test MySQL"
        assert conn["db_type"] == "mysql"
        assert conn["host"] == "localhost"
        assert conn["port"] == 3306
        assert conn["database"] == "testdb"
        assert conn["username"] == "root"
        # Password should NOT be in summary
        assert "password" not in conn
        assert conn["passwordSet"] is True
        assert conn["verified"] is False

    def test_create_sqlite_connection_no_password(self, sqlite_env):
        store = SqliteConnectionStore()
        conn = store.create({
            "name": "Local SQLite", "db_type": "sqlite",
            "file_path": "/tmp/test.db",
        })
        assert conn["db_type"] == "sqlite"
        assert conn["host"] == "/tmp/test.db"  # file_path shown as host
        assert conn["passwordSet"] is False
        assert "port" not in conn  # sqlite summary excludes port

    def test_list_all_returns_all(self, sqlite_env):
        store = SqliteConnectionStore()
        store.create({"name": "A", "db_type": "sqlite", "file_path": "/tmp/a.db"})
        store.create({"name": "B", "db_type": "sqlite", "file_path": "/tmp/b.db"})
        all_conns = store.list_all()
        assert len(all_conns) == 2
        names = {c["name"] for c in all_conns}
        assert names == {"A", "B"}

    def test_get_returns_summary(self, sqlite_env):
        store = SqliteConnectionStore()
        created = store.create({
            "name": "PG", "db_type": "postgresql",
            "host": "pg.example.com", "port": 5432,
            "database": "prod", "username": "admin", "password": "s3cr3t",
        })
        fetched = store.get(created["id"])
        assert fetched is not None
        assert fetched["name"] == "PG"
        assert fetched["host"] == "pg.example.com"

    def test_get_nonexistent_returns_none(self, sqlite_env):
        store = SqliteConnectionStore()
        assert store.get("nonexistent-id") is None

    def test_get_with_plaintext_password_decrypts(self, sqlite_env):
        store = SqliteConnectionStore()
        created = store.create({
            "name": "Enc", "db_type": "mysql",
            "host": "h", "port": 1, "database": "d",
            "username": "u", "password": "my-secret-pwd",
        })
        full = store.get_with_plaintext_password(created["id"])
        assert full is not None
        assert full["password"] == "my-secret-pwd"  # Decrypted plaintext

    def test_password_is_encrypted_in_db(self, sqlite_env):
        """DB 中存储的 password 字段应为 Fernet 密文，不是明文。"""
        store = SqliteConnectionStore()
        store.create({
            "name": "Enc", "db_type": "mysql",
            "host": "h", "port": 1, "database": "d",
            "username": "u", "password": "plaintext-secret",
        })
        # Read raw row from DB
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                connections_table.select().limit(1)
            ).fetchone()
        assert row is not None
        db_password = row._mapping["password"]
        assert db_password != "plaintext-secret"
        assert len(db_password) > 50  # Fernet ciphertext is long

    def test_update_changes_fields(self, sqlite_env):
        store = SqliteConnectionStore()
        created = store.create({
            "name": "Orig", "db_type": "mysql",
            "host": "h1", "port": 1, "database": "d1",
            "username": "u1", "password": "p1",
        })
        updated = store.update(created["id"], {
            "name": "Updated", "host": "h2", "password": "new-pwd",
        })
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["host"] == "h2"
        # Verify new password decrypts correctly
        full = store.get_with_plaintext_password(created["id"])
        assert full["password"] == "new-pwd"

    def test_update_nonexistent_returns_none(self, sqlite_env):
        store = SqliteConnectionStore()
        assert store.update("no-such-id", {"name": "X"}) is None

    def test_delete_removes_connection(self, sqlite_env):
        store = SqliteConnectionStore()
        created = store.create({"name": "Tmp", "db_type": "sqlite", "file_path": "/tmp/x.db"})
        assert store.delete(created["id"]) is True
        assert store.get(created["id"]) is None
        # Second delete returns False
        assert store.delete(created["id"]) is False

    def test_update_verified_sets_flag(self, sqlite_env):
        store = SqliteConnectionStore()
        created = store.create({
            "name": "V", "db_type": "mysql",
            "host": "h", "port": 1, "database": "d",
            "username": "u", "password": "p",
        })
        assert created["verified"] is False
        store.update_verified(created["id"], True)
        fetched = store.get(created["id"])
        assert fetched["verified"] is True

    def test_build_connection_string_delegates(self, sqlite_env):
        """build_connection_string 应委托给现有 ConnectionStore（纯逻辑）。"""
        store = SqliteConnectionStore()
        entry = {
            "db_type": "mysql",
            "host": "localhost", "port": 3306,
            "database": "test", "username": "root",
            "password": "secret",
        }
        cs = store.build_connection_string(entry)
        assert "mysql" in cs.lower() or "pymysql" in cs.lower()
        assert "root" in cs
        assert "secret" in cs


# ---------------------------------------------------------------------------
# SqliteTemplateStore
# ---------------------------------------------------------------------------


class TestSqliteTemplateStore:
    """TemplateStore — CRUD + JSON 字段序列化 + requirements 提取。"""

    def _sample_config_state(self) -> dict:
        return {
            "current_step": 5,
            "scene": {"name": "Test", "description": "Test scene"},
            "inputs": [{"name": "src", "plugin": "csv", "paramKey": "src",
                        "config": {"type": "csv"}}],
            "processors": [{"name": "proc", "plugin": "sql", "sql": "SELECT 1"}],
            "output": {"plugin": "csv", "config": {"type": "csv"}},
        }

    def test_create_template_returns_dict(self, sqlite_env):
        store = SqliteTemplateStore()
        tmpl = store.create_template(
            name="My Template", description="A test template",
            category="data-processing", tags=["tag1", "tag2"],
            config_state=self._sample_config_state(),
            author="tester", is_official=False,
        )
        assert tmpl["name"] == "My Template"
        assert tmpl["description"] == "A test template"
        assert tmpl["category"] == "data-processing"
        assert tmpl["tags"] == ["tag1", "tag2"]
        assert tmpl["author"] == "tester"
        assert tmpl["is_official"] is False
        assert tmpl["usage_count"] == 0
        assert "id" in tmpl and len(tmpl["id"]) > 0

    def test_list_templates_empty(self, sqlite_env):
        store = SqliteTemplateStore()
        assert store.list_templates() == []

    def test_list_templates_with_category_filter(self, sqlite_env):
        store = SqliteTemplateStore()
        store.create_template("A", "desc", "cat1", [], {}, author="x")
        store.create_template("B", "desc", "cat2", [], {}, author="x")
        result = store.list_templates(category="cat1")
        assert len(result) == 1
        assert result[0]["name"] == "A"

    def test_list_templates_with_search(self, sqlite_env):
        store = SqliteTemplateStore()
        store.create_template("Data Cleaner", "cleans data", "cat", ["clean"], {}, author="x")
        store.create_template("Aggregator", "aggregates", "cat", ["agg"], {}, author="x")
        # Search by name
        result = store.list_templates(search="clean")
        assert len(result) == 1
        assert result[0]["name"] == "Data Cleaner"
        # Search by tag
        result = store.list_templates(search="agg")
        assert len(result) == 1
        assert result[0]["name"] == "Aggregator"

    def test_get_template_returns_none_for_missing(self, sqlite_env):
        store = SqliteTemplateStore()
        assert store.get_template("nonexistent") is None

    def test_config_state_round_trips_through_json(self, sqlite_env):
        """config_state 字段应通过 JSON 序列化/反序列化保持完整。"""
        store = SqliteTemplateStore()
        cs = self._sample_config_state()
        created = store.create_template("T", "d", "c", [], cs, author="x")
        fetched = store.get_template(created["id"])
        assert fetched is not None
        assert fetched["config_state"] == cs

    def test_update_template(self, sqlite_env):
        store = SqliteTemplateStore()
        created = store.create_template("Orig", "desc", "cat", [], {}, author="x")
        updated = store.update_template(created["id"], name="Updated", description="New desc")
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["description"] == "New desc"

    def test_update_template_nonexistent_returns_none(self, sqlite_env):
        store = SqliteTemplateStore()
        assert store.update_template("no-such-id", name="X") is None

    def test_delete_template(self, sqlite_env):
        store = SqliteTemplateStore()
        created = store.create_template("T", "d", "c", [], {}, author="x")
        assert store.delete_template(created["id"]) is True
        assert store.get_template(created["id"]) is None
        assert store.delete_template(created["id"]) is False

    def test_increment_usage(self, sqlite_env):
        store = SqliteTemplateStore()
        created = store.create_template("T", "d", "c", [], {}, author="x")
        store.increment_usage(created["id"])
        store.increment_usage(created["id"])
        fetched = store.get_template(created["id"])
        assert fetched["usage_count"] == 2

    def test_official_templates_sort_first(self, sqlite_env):
        store = SqliteTemplateStore()
        store.create_template("Unofficial A", "d", "c", [], {}, author="x", is_official=False)
        store.create_template("Official B", "d", "c", [], {}, author="x", is_official=True)
        result = store.list_templates()
        assert result[0]["name"] == "Official B"


# ---------------------------------------------------------------------------
# SqliteUserStore
# ---------------------------------------------------------------------------


class TestSqliteUserStore:
    """UserStore — CRUD + 密码哈希 + 认证。"""

    def test_ensure_default_admin_creates_admin(self, sqlite_env):
        store = SqliteUserStore()
        store.ensure_default_admin()
        users = store.list_users()
        assert len(users) == 1
        assert users[0].username == "admin"
        assert users[0].role == "admin"

    def test_ensure_default_admin_idempotent(self, sqlite_env):
        store = SqliteUserStore()
        store.ensure_default_admin()
        store.ensure_default_admin()  # Should not duplicate
        assert len(store.list_users()) == 1

    def test_authenticate_admin_with_default_password(self, sqlite_env):
        store = SqliteUserStore()
        store.ensure_default_admin()
        user = store.authenticate("admin", "admin123")
        assert user is not None
        assert user.username == "admin"
        assert user.must_change_password is True

    def test_authenticate_wrong_password_returns_none(self, sqlite_env):
        store = SqliteUserStore()
        store.ensure_default_admin()
        assert store.authenticate("admin", "wrong-password") is None

    def test_authenticate_nonexistent_user_returns_none(self, sqlite_env):
        store = SqliteUserStore()
        assert store.authenticate("nobody", "pwd") is None

    def test_create_user(self, sqlite_env):
        store = SqliteUserStore()
        user = store.create_user("alice", "alice-password", role="editor")
        assert user is not None
        assert user.username == "alice"
        assert user.role == "editor"
        # Should authenticate
        authed = store.authenticate("alice", "alice-password")
        assert authed is not None
        assert authed.username == "alice"

    def test_create_user_duplicate_returns_none(self, sqlite_env):
        store = SqliteUserStore()
        store.create_user("bob", "pwd1")
        # Same username again
        assert store.create_user("bob", "pwd2") is None

    def test_delete_user(self, sqlite_env):
        store = SqliteUserStore()
        user = store.create_user("charlie", "pwd")
        assert store.delete_user(user.id) is True
        assert store.get_user_by_id(user.id) is None
        assert store.delete_user(user.id) is False

    def test_change_password(self, sqlite_env):
        store = SqliteUserStore()
        user = store.create_user("dave", "old-pwd")
        # Wrong old password
        assert store.change_password(user.id, "wrong", "new-pwd") is False
        # Correct old password
        assert store.change_password(user.id, "old-pwd", "new-pwd") is True
        # New password works
        assert store.authenticate("dave", "new-pwd") is not None
        # Old password fails
        assert store.authenticate("dave", "old-pwd") is None

    def test_change_password_nonexistent_returns_false(self, sqlite_env):
        store = SqliteUserStore()
        assert store.change_password("no-such-id", "old", "new") is False

    def test_password_hash_not_stored_as_plaintext(self, sqlite_env):
        """DB 中存储的 password_hash 应为哈希值，不是明文。"""
        store = SqliteUserStore()
        store.create_user("eve", "my-secret-password")
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                users_table.select().where(users_table.c.username == "eve")
            ).fetchone()
        assert row is not None
        hash_val = row._mapping["password_hash"]
        assert hash_val != "my-secret-password"
        # SHA256 hash format: "sha256$salt$hash"
        assert hash_val.startswith("sha256$")


# ---------------------------------------------------------------------------
# SqliteAuditStore
# ---------------------------------------------------------------------------


class TestSqliteAuditStore:
    """AuditStore — log_audit + get_audit_log + 过滤 + 自动修剪。"""

    def test_log_audit_creates_entry(self, sqlite_env):
        store = SqliteAuditStore()
        store.log_audit("create", "connection", "conn-1", {"user": "admin"})
        entries = store.get_audit_log()
        assert len(entries) == 1
        assert entries[0]["action"] == "create"
        assert entries[0]["target_type"] == "connection"
        assert entries[0]["target_id"] == "conn-1"
        assert entries[0]["details"] == {"user": "admin"}

    def test_get_audit_log_chronological_order(self, sqlite_env):
        """get_audit_log 应按时间顺序返回（最旧在前）。"""
        store = SqliteAuditStore()
        store.log_audit("action1", "type1", "id1")
        store.log_audit("action2", "type1", "id2")
        store.log_audit("action3", "type1", "id3")
        entries = store.get_audit_log()
        assert len(entries) == 3
        # Should be in insertion order (chronological)
        assert entries[0]["action"] == "action1"
        assert entries[2]["action"] == "action3"

    def test_filter_by_target_type(self, sqlite_env):
        store = SqliteAuditStore()
        store.log_audit("a", "connection", "id1")
        store.log_audit("b", "template", "id2")
        store.log_audit("c", "connection", "id3")
        entries = store.get_audit_log(target_type="connection")
        assert len(entries) == 2
        assert all(e["target_type"] == "connection" for e in entries)

    def test_filter_by_action(self, sqlite_env):
        store = SqliteAuditStore()
        store.log_audit("create", "t", "id1")
        store.log_audit("delete", "t", "id2")
        store.log_audit("create", "t", "id3")
        entries = store.get_audit_log(action="create")
        assert len(entries) == 2
        assert all(e["action"] == "create" for e in entries)

    def test_filter_by_user(self, sqlite_env):
        """user filter matches target_id OR details.user."""
        store = SqliteAuditStore()
        store.log_audit("a", "t", "alice-target", {"user": "alice"})
        store.log_audit("b", "t", "bob-target", {"user": "bob"})
        store.log_audit("c", "t", "shared-target", {"user": "alice"})
        # user="alice" matches entry1 (details.user) + entry3 (details.user) = 2
        alice_entries = store.get_audit_log(user="alice")
        assert len(alice_entries) == 2
        # user="bob" matches entry2 (target_id AND details.user) = 1
        bob_entries = store.get_audit_log(user="bob")
        assert len(bob_entries) == 1
        assert bob_entries[0]["target_id"] == "bob-target"

    def test_limit_param(self, sqlite_env):
        store = SqliteAuditStore()
        for i in range(10):
            store.log_audit(f"action{i}", "type", f"id{i}")
        entries = store.get_audit_log(limit=5)
        # limit=5 returns the 5 most recent (then reversed to chronological)
        assert len(entries) == 5
        # Should be the last 5 inserted (id5..id9), in chronological order
        assert entries[0]["target_id"] == "id5"
        assert entries[4]["target_id"] == "id9"

    def test_auto_trim_when_exceeding_max_entries(self, sqlite_env, monkeypatch):
        """超过 MAX_ENTRIES 时应自动删除最旧记录。"""
        store = SqliteAuditStore()
        # Lower the threshold for testing
        monkeypatch.setattr(SqliteAuditStore, "MAX_ENTRIES", 5)
        # Insert 7 entries; after each insert, store trims to 5
        for i in range(7):
            store.log_audit("a", "t", f"id{i}")
        entries = store.get_audit_log(limit=100)
        assert len(entries) == 5
        # Oldest 2 (id0, id1) should be removed
        ids = [e["target_id"] for e in entries]
        assert "id0" not in ids
        assert "id1" not in ids
        assert "id2" in ids
        assert "id6" in ids


# ---------------------------------------------------------------------------
# SqliteSettingsStore
# ---------------------------------------------------------------------------


class TestSqliteSettingsStore:
    """SettingsStore — SMTP/AI 设置的加载/保存 + Fernet 加解密。"""

    def test_load_default_smtp_when_empty(self, sqlite_env):
        store = SqliteSettingsStore(kind="smtp")
        settings = store.load_settings()
        # Default SmtpSettings
        assert settings.host == ""
        assert settings.port == 587
        assert settings.use_tls is True

    def test_save_and_load_smtp_settings_round_trip(self, sqlite_env):
        from configforge.services.notifier.smtp_settings import SmtpSettings

        store = SqliteSettingsStore(kind="smtp")
        original = SmtpSettings(
            host="smtp.example.com", port=465, user="sender",
            password="smtp-secret-password", use_tls=False,
            sender="sender@example.com",
        )
        store.save_settings(original)
        loaded = store.load_settings()
        assert loaded.host == "smtp.example.com"
        assert loaded.port == 465
        assert loaded.user == "sender"
        assert loaded.password == "smtp-secret-password"  # Decrypted
        assert loaded.use_tls is False
        assert loaded.sender == "sender@example.com"

    def test_smtp_password_is_encrypted_in_db(self, sqlite_env):
        """DB 中存储的 SMTP password 应为 Fernet 密文。"""
        from configforge.services.notifier.smtp_settings import SmtpSettings

        store = SqliteSettingsStore(kind="smtp")
        store.save_settings(SmtpSettings(
            host="h", port=587, user="u",
            password="plaintext-smtp-pwd", use_tls=True, sender="s@x.com",
        ))
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                settings_table.select().where(settings_table.c.kind == "smtp")
            ).fetchone()
        raw = json.loads(row._mapping["data"])
        assert raw["password"] != "plaintext-smtp-pwd"
        assert len(raw["password"]) > 50  # Fernet ciphertext

    def test_save_and_load_ai_settings_round_trip(self, sqlite_env):
        from configforge.models.ai import AiProvider, AiSettings

        store = SqliteSettingsStore(kind="ai")
        original = AiSettings(
            provider=AiProvider.CUSTOM,
            api_key="ai-secret-key-xxx",
            base_url="https://api.example.com",
            model="gpt-test",
            temperature=0.5,
            max_tokens=2048,
            enabled=True,
        )
        store.save_settings(original)
        loaded = store.load_settings()
        assert loaded.provider == AiProvider.CUSTOM
        assert loaded.api_key == "ai-secret-key-xxx"  # Decrypted
        assert loaded.base_url == "https://api.example.com"
        assert loaded.model == "gpt-test"
        assert loaded.temperature == 0.5
        assert loaded.max_tokens == 2048
        assert loaded.enabled is True

    def test_ai_api_key_is_encrypted_in_db(self, sqlite_env):
        from configforge.models.ai import AiProvider, AiSettings

        store = SqliteSettingsStore(kind="ai")
        store.save_settings(AiSettings(
            provider=AiProvider.OPENAI,
            api_key="plaintext-ai-key",
            base_url="", model="", temperature=0.7, max_tokens=4096, enabled=False,
        ))
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                settings_table.select().where(settings_table.c.kind == "ai")
            ).fetchone()
        raw = json.loads(row._mapping["data"])
        assert raw["api_key"] != "plaintext-ai-key"
        assert len(raw["api_key"]) > 50

    def test_save_settings_upsert(self, sqlite_env):
        """重复保存应更新而非插入。"""
        from configforge.services.notifier.smtp_settings import SmtpSettings

        store = SqliteSettingsStore(kind="smtp")
        store.save_settings(SmtpSettings(host="h1", port=587, user="u1", password="", use_tls=True, sender="s1@x.com"))
        store.save_settings(SmtpSettings(host="h2", port=465, user="u2", password="", use_tls=False, sender="s2@x.com"))

        # Should only have 1 row (upsert, not insert)
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                settings_table.select().where(settings_table.c.kind == "smtp")
            ).fetchall()
        assert len(rows) == 1
        # Loaded settings should have the latest values
        loaded = store.load_settings()
        assert loaded.host == "h2"
        assert loaded.port == 465

    def test_unknown_kind_raises_value_error(self, sqlite_env):
        store = SqliteSettingsStore(kind="unknown")
        with pytest.raises(ValueError, match="Unknown settings kind"):
            store.load_settings()


# ---------------------------------------------------------------------------
# SqliteScheduleStore
# ---------------------------------------------------------------------------


class TestSqliteScheduleStore:
    """ScheduleStore — CRUD + cron 验证 + 调度器同步注册（T-5E-04）。"""

    def test_add_schedule_returns_dict(self, sqlite_env):
        store = SqliteScheduleStore()
        sched = store.add_schedule({
            "config_id": "cfg-1",
            "cron_expression": "0 8 * * *",
            "description": "Daily 8am",
            "retry_count": 2,
            "retry_interval": 600,
        })
        assert sched["config_id"] == "cfg-1"
        assert sched["cron_expression"] == "0 8 * * *"
        assert sched["description"] == "Daily 8am"
        assert sched["retry_count"] == 2
        assert sched["retry_interval"] == 600
        assert sched["enabled"] is True
        assert "id" in sched and len(sched["id"]) > 0

    def test_add_schedule_invalid_cron_raises(self, sqlite_env):
        store = SqliteScheduleStore()
        with pytest.raises((ValueError, Exception)):
            store.add_schedule({
                "config_id": "cfg-1",
                "cron_expression": "invalid-cron",
            })

    def test_add_schedule_wrong_field_count_raises(self, sqlite_env):
        store = SqliteScheduleStore()
        with pytest.raises(ValueError, match="5 fields"):
            store.add_schedule({
                "config_id": "cfg-1",
                "cron_expression": "0 8 * * *  extra",  # 6 fields
            })

    def test_list_schedules_empty(self, sqlite_env):
        store = SqliteScheduleStore()
        assert store.list_schedules() == []

    def test_list_schedules_returns_all(self, sqlite_env):
        store = SqliteScheduleStore()
        store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        store.add_schedule({"config_id": "c2", "cron_expression": "0 9 * * *"})
        scheds = store.list_schedules()
        assert len(scheds) == 2

    def test_update_schedule(self, sqlite_env):
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        updated = store.update_schedule(created["id"], description="Updated desc", retry_count=5)
        assert updated is not None
        assert updated["description"] == "Updated desc"
        assert updated["retry_count"] == 5
        # cron should be unchanged
        assert updated["cron_expression"] == "0 8 * * *"

    def test_update_schedule_cron_expression(self, sqlite_env):
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        updated = store.update_schedule(created["id"], cron_expression="0 12 * * *")
        assert updated is not None
        assert updated["cron_expression"] == "0 12 * * *"

    def test_update_schedule_invalid_cron_raises(self, sqlite_env):
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        with pytest.raises((ValueError, Exception)):
            store.update_schedule(created["id"], cron_expression="bad-cron")

    def test_update_schedule_nonexistent_returns_none(self, sqlite_env):
        store = SqliteScheduleStore()
        assert store.update_schedule("no-such-id", description="x") is None

    def test_remove_schedule(self, sqlite_env):
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        assert store.remove_schedule(created["id"]) is True
        assert store.list_schedules() == []
        assert store.remove_schedule(created["id"]) is False

    def test_toggle_schedule_disables(self, sqlite_env):
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        assert created["enabled"] is True
        toggled = store.toggle_schedule(created["id"])
        assert toggled is not None
        assert toggled["enabled"] is False
        # Toggle again re-enables
        toggled2 = store.toggle_schedule(created["id"])
        assert toggled2["enabled"] is True

    def test_toggle_schedule_nonexistent_returns_none(self, sqlite_env):
        store = SqliteScheduleStore()
        assert store.toggle_schedule("no-such-id") is None

    # ── T-5E-04: 调度器同步注册测试 ──

    def test_add_schedule_registers_job(self, sqlite_env, monkeypatch):
        """T-5E-04: add_schedule 应同步注册 BackgroundScheduler 任务。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        mock_sched.add_job.assert_called_once()
        # Verify job id matches schedule id
        call_kwargs = mock_sched.add_job.call_args
        assert call_kwargs.kwargs["id"] == created["id"]

    def test_add_schedule_no_scheduler_no_crash(self, sqlite_env, monkeypatch):
        """T-5E-04: scheduler 未启动时 add_schedule 不应崩溃。"""
        from configforge import scheduler

        monkeypatch.setattr(scheduler, "_scheduler", None)
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        assert created["id"]  # Schedule still persisted

    def test_update_schedule_reregisters_job(self, sqlite_env, monkeypatch):
        """T-5E-04: update_schedule 应重新注册 job（enabled 时）。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        mock_sched.reset_mock()

        store.update_schedule(created["id"], cron_expression="0 9 * * *")
        mock_sched.remove_job.assert_called_once_with(created["id"])
        mock_sched.add_job.assert_called_once()

    def test_update_schedule_disabled_no_reregister(self, sqlite_env, monkeypatch):
        """T-5E-04: update_schedule 对 disabled 的任务不应操作调度器。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        store.toggle_schedule(created["id"])  # disable
        mock_sched.reset_mock()

        store.update_schedule(created["id"], cron_expression="0 9 * * *")
        mock_sched.remove_job.assert_not_called()
        mock_sched.add_job.assert_not_called()

    def test_remove_schedule_unregisters_job(self, sqlite_env, monkeypatch):
        """T-5E-04: remove_schedule 应移除 BackgroundScheduler 任务。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        mock_sched.reset_mock()

        assert store.remove_schedule(created["id"]) is True
        mock_sched.remove_job.assert_called_once_with(created["id"])

    def test_toggle_schedule_disables_unregisters(self, sqlite_env, monkeypatch):
        """T-5E-04: toggle 禁用时应移除 job。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        mock_sched.reset_mock()

        result = store.toggle_schedule(created["id"])
        assert result["enabled"] is False
        mock_sched.remove_job.assert_called_once_with(created["id"])
        mock_sched.add_job.assert_not_called()

    def test_toggle_schedule_enables_registers(self, sqlite_env, monkeypatch):
        """T-5E-04: toggle 启用时应注册 job。"""
        from configforge import scheduler

        mock_sched = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_sched)

        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})
        store.toggle_schedule(created["id"])  # disable
        mock_sched.reset_mock()

        result = store.toggle_schedule(created["id"])  # re-enable
        assert result["enabled"] is True
        mock_sched.add_job.assert_called_once()

    def test_update_last_run_success(self, sqlite_env):
        """T-5E-04: update_last_run 应写入 last_run_at 和 last_run_status。"""
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})

        store.update_last_run(created["id"], "success")
        schedules = store.list_schedules()
        s = [x for x in schedules if x["id"] == created["id"]][0]
        assert s["last_run_status"] == "success"
        assert s["last_run_at"] is not None

    def test_update_last_run_failed(self, sqlite_env):
        """T-5E-04: update_last_run 支持 'failed' 状态。"""
        store = SqliteScheduleStore()
        created = store.add_schedule({"config_id": "c1", "cron_expression": "0 8 * * *"})

        store.update_last_run(created["id"], "failed")
        schedules = store.list_schedules()
        s = [x for x in schedules if x["id"] == created["id"]][0]
        assert s["last_run_status"] == "failed"

    def test_update_last_run_nonexistent_silent(self, sqlite_env):
        """T-5E-04: update_last_run 对不存在的 schedule 应静默无操作。"""
        store = SqliteScheduleStore()
        # Should not raise
        store.update_last_run("no-such-id", "success")
