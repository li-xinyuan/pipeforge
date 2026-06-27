"""JSON → SQLite 迁移脚本单测 (T-5E-02)。

验证：
- dry-run 不写入 DB
- 实际迁移正确写入
- 幂等性（重复运行 skip）
- 加密字段（password、api_key）保持不变
- 用户密码哈希保持不变
- JSON 字段（tags、config_state）正确序列化
"""
from __future__ import annotations

import json
import os

from configforge.storage.sqlite_schema import (
    audit_log_table,
    connections_table,
    get_engine,
    settings_table,
    templates_table,
    users_table,
)
from configforge.utils.crypto import get_cipher


def _write_json(path: str, data) -> None:
    """Write data as JSON to path, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _count_rows(table) -> int:
    """Count rows in a table."""
    from sqlalchemy import func, select
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(table)).scalar() or 0


class TestMigrateDryRun:
    """dry-run 模式不应写入数据库。"""

    def test_dry_run_creates_no_rows(self, sqlite_env):
        # Prepare a small JSON file
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "db_connections.json"),
            {"connections": {"c1": {"name": "C1", "db_type": "sqlite", "file_path": "/tmp/x.db"}}},
        )

        from configforge.utils.migrate_to_sqlite import migrate_connections
        m, s = migrate_connections(dry_run=True)
        assert m == 1  # Reports 1 to migrate
        assert s == 0
        # DB should be empty
        assert _count_rows(connections_table) == 0


class TestMigrateConnections:
    """Connection 迁移测试。"""

    def test_migrate_connections_basic(self, sqlite_env):
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "db_connections.json"),
            {"connections": {
                "c1": {"name": "C1", "db_type": "sqlite", "file_path": "/tmp/x.db",
                       "verified": False, "created_at": "2024-01-01T00:00:00Z",
                       "updated_at": "2024-01-01T00:00:00Z"},
                "c2": {"name": "C2", "db_type": "mysql", "host": "h", "port": 3306,
                       "database": "d", "username": "u", "password": "encrypted-cipher-text",
                       "verified": True, "created_at": "2024-01-01T00:00:00Z",
                       "updated_at": "2024-01-01T00:00:00Z"},
            }},
        )

        from configforge.utils.migrate_to_sqlite import migrate_connections
        m, s = migrate_connections(dry_run=False)
        assert m == 2
        assert s == 0
        assert _count_rows(connections_table) == 2

    def test_migrate_preserves_encrypted_password(self, sqlite_env):
        """加密的 password 字段应直接复制，不重新加密。"""
        data_dir = sqlite_env["data_dir"]
        # Create a real Fernet-encrypted password
        cipher = get_cipher()
        plaintext = "my-db-password"
        encrypted = cipher.encrypt(plaintext.encode()).decode()

        _write_json(
            os.path.join(data_dir, "db_connections.json"),
            {"connections": {
                "c1": {"name": "C1", "db_type": "mysql", "host": "h", "port": 3306,
                       "database": "d", "username": "u", "password": encrypted,
                       "verified": False, "created_at": "2024-01-01T00:00:00Z",
                       "updated_at": "2024-01-01T00:00:00Z"},
            }},
        )

        from configforge.utils.migrate_to_sqlite import migrate_connections
        migrate_connections(dry_run=False)

        # Read raw DB row
        from sqlalchemy import select
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(select(connections_table).limit(1)).fetchone()
        db_password = row._mapping["password"]
        # DB password should be the same ciphertext (not re-encrypted)
        assert db_password == encrypted
        # And should decrypt to the original plaintext
        assert cipher.decrypt(db_password.encode()).decode() == plaintext

    def test_migrate_idempotent(self, sqlite_env):
        """重复运行迁移应跳过已存在的记录。"""
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "db_connections.json"),
            {"connections": {
                "c1": {"name": "C1", "db_type": "sqlite", "file_path": "/tmp/x.db",
                       "verified": False, "created_at": "2024-01-01T00:00:00Z",
                       "updated_at": "2024-01-01T00:00:00Z"},
            }},
        )

        from configforge.utils.migrate_to_sqlite import migrate_connections
        m1, s1 = migrate_connections(dry_run=False)
        assert (m1, s1) == (1, 0)
        m2, s2 = migrate_connections(dry_run=False)
        assert (m2, s2) == (0, 1)  # Skipped
        assert _count_rows(connections_table) == 1  # Not doubled


class TestMigrateUsers:
    """User 迁移测试。"""

    def test_migrate_users_preserves_password_hash(self, sqlite_env):
        """用户密码哈希应直接复制，不重新哈希。"""
        data_dir = sqlite_env["data_dir"]
        # Use a real hash (matching user_store format)
        from configforge.services.user_store import _hash_password
        real_hash = _hash_password("test-password")

        _write_json(
            os.path.join(data_dir, "users.json"),
            {"users": {
                "u1": {"username": "alice", "role": "admin",
                       "password_hash": real_hash,
                       "created_at": "2024-01-01T00:00:00Z",
                       "must_change_password": False},
            }},
        )

        from configforge.utils.migrate_to_sqlite import migrate_users
        m, s = migrate_users(dry_run=False)
        assert (m, s) == (1, 0)

        # Verify hash copied correctly
        from sqlalchemy import select
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(select(users_table).limit(1)).fetchone()
        assert row._mapping["password_hash"] == real_hash
        assert row._mapping["username"] == "alice"
        assert row._mapping["role"] == "admin"

    def test_migrate_users_idempotent(self, sqlite_env):
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "users.json"),
            {"users": {
                "u1": {"username": "alice", "role": "admin", "password_hash": "hash$abc",
                       "created_at": "2024-01-01T00:00:00Z"},
            }},
        )
        from configforge.utils.migrate_to_sqlite import migrate_users
        assert migrate_users(dry_run=False) == (1, 0)
        assert migrate_users(dry_run=False) == (0, 1)


class TestMigrateTemplates:
    """Template 迁移测试。"""

    def test_migrate_templates_json_fields(self, sqlite_env):
        """tags、config_state 等 JSON 字段应正确序列化。"""
        data_dir = sqlite_env["data_dir"]
        config_state = {"scene": {"name": "Test"}, "inputs": []}
        tags = ["tag1", "tag2"]

        _write_json(
            os.path.join(data_dir, "templates.json"),
            {"templates": {
                "t1": {"name": "T1", "description": "desc", "category": "cat",
                       "tags": tags, "author": "a", "version": "1.0",
                       "config_state": config_state, "requirements": [],
                       "usage_count": 5, "is_official": True,
                       "created_at": "2024-01-01T00:00:00Z",
                       "updated_at": "2024-01-01T00:00:00Z"},
            }},
        )

        from configforge.utils.migrate_to_sqlite import migrate_templates
        m, s = migrate_templates(dry_run=False)
        assert (m, s) == (1, 0)

        # Verify JSON fields round-trip
        from sqlalchemy import select
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(select(templates_table).limit(1)).fetchone()
        assert json.loads(row._mapping["tags"]) == tags
        assert json.loads(row._mapping["config_state"]) == config_state
        assert row._mapping["usage_count"] == 5
        assert row._mapping["is_official"] == 1


class TestMigrateSettings:
    """Settings 迁移测试。"""

    def test_migrate_smtp_settings(self, sqlite_env):
        data_dir = sqlite_env["data_dir"]
        cipher = get_cipher()
        encrypted_pwd = cipher.encrypt(b"smtp-pwd").decode()
        settings_data = {
            "host": "smtp.test.com", "port": 587, "user": "u",
            "password": encrypted_pwd, "use_tls": True, "sender": "s@x.com",
        }
        _write_json(os.path.join(data_dir, "smtp_settings.json"), settings_data)

        from configforge.utils.migrate_to_sqlite import migrate_settings
        m, s = migrate_settings("smtp", dry_run=False)
        assert (m, s) == (1, 0)

        # Verify data preserved
        from sqlalchemy import select
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                select(settings_table).where(settings_table.c.kind == "smtp")
            ).fetchone()
        raw = json.loads(row._mapping["data"])
        assert raw["host"] == "smtp.test.com"
        assert raw["password"] == encrypted_pwd  # Ciphertext preserved

    def test_migrate_settings_missing_file(self, sqlite_env):
        """文件不存在时应返回 (0, 0)。"""
        from configforge.utils.migrate_to_sqlite import migrate_settings
        m, s = migrate_settings("smtp", dry_run=False)
        assert (m, s) == (0, 0)

    def test_migrate_settings_idempotent(self, sqlite_env):
        data_dir = sqlite_env["data_dir"]
        _write_json(os.path.join(data_dir, "smtp_settings.json"), {"host": "h", "port": 587})
        from configforge.utils.migrate_to_sqlite import migrate_settings
        assert migrate_settings("smtp", dry_run=False) == (1, 0)
        assert migrate_settings("smtp", dry_run=False) == (0, 1)


class TestMigrateAuditLog:
    """Audit log 迁移测试。"""

    def test_migrate_audit_log_basic(self, sqlite_env):
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "audit_log.json"),
            [
                {"timestamp": "2024-01-01T00:00:00Z", "action": "create",
                 "target_type": "connection", "target_id": "c1", "details": {"user": "admin"}},
                {"timestamp": "2024-01-01T01:00:00Z", "action": "delete",
                 "target_type": "connection", "target_id": "c1", "details": {}},
            ],
        )

        from configforge.utils.migrate_to_sqlite import migrate_audit_log
        m, s = migrate_audit_log(dry_run=False)
        assert m == 2
        assert _count_rows(audit_log_table) == 2

    def test_migrate_audit_log_skips_non_empty_table(self, sqlite_env):
        """audit_log 表非空时应跳过迁移（避免重复）。"""
        data_dir = sqlite_env["data_dir"]
        _write_json(
            os.path.join(data_dir, "audit_log.json"),
            [{"timestamp": "2024-01-01T00:00:00Z", "action": "a", "target_type": "t",
              "target_id": "i", "details": {}}],
        )

        from configforge.utils.migrate_to_sqlite import migrate_audit_log
        # First migration
        m1, _ = migrate_audit_log(dry_run=False)
        assert m1 == 1
        # Second migration should skip (table non-empty)
        m2, _ = migrate_audit_log(dry_run=False)
        assert m2 == 0
        assert _count_rows(audit_log_table) == 1  # Not doubled


class TestMigrateEmptyData:
    """空数据迁移测试。"""

    def test_migrate_with_no_json_files(self, sqlite_env):
        """没有 JSON 文件时应正常完成（迁移 0 条）。"""
        from configforge.utils.migrate_to_sqlite import (
            migrate_audit_log,
            migrate_connections,
            migrate_schedules,
            migrate_settings,
            migrate_templates,
            migrate_users,
        )
        assert migrate_connections(dry_run=False) == (0, 0)
        assert migrate_templates(dry_run=False) == (0, 0)
        assert migrate_users(dry_run=False) == (0, 0)
        assert migrate_schedules(dry_run=False) == (0, 0)
        assert migrate_audit_log(dry_run=False) == (0, 0)
        assert migrate_settings("smtp", dry_run=False) == (0, 0)
        assert migrate_settings("ai", dry_run=False) == (0, 0)
