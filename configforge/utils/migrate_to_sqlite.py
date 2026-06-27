"""JSON → SQLite 数据迁移脚本 (T-5E-02)。

将所有 JSON 存储的数据迁移到 SQLite 数据库。
加密字段（密码、API key）在 JSON 中已 Fernet 加密，可直接复制到 SQLite，无需重新加密。
用户密码哈希同样可直接复制。

用法：
    python -m configforge.utils.migrate_to_sqlite [--dry-run] [--sqlite-path PATH]

选项：
    --dry-run       只打印迁移计划，不实际写入
    --sqlite-path   指定 SQLite 数据库路径（默认 data/configforge.db）

注意：
- 迁移是幂等的：重复运行会跳过已存在的记录
- Configs（pipeline 配置）仍使用 JSON 文件存储，不在此次迁移范围内
- 迁移后需设置 CONFIGFORGE_STORAGE_BACKEND=sqlite 才能使用 SQLite 后端
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from sqlalchemy import insert, select

from configforge.storage.sqlite_schema import (
    audit_log_table,
    connections_table,
    get_engine,
    get_sqlite_path,
    init_schema,
    schedules_table,
    settings_table,
    templates_table,
    users_table,
)
from configforge.utils.migration import load_with_migration
from configforge.utils.paths import get_data_dir


def _load_json(path: str, default: Any) -> Any:
    """Load JSON file with migration support, return default if not exists."""
    if not os.path.exists(path):
        return default
    return load_with_migration(path, default=default)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def migrate_connections(dry_run: bool = False) -> tuple[int, int]:
    """Migrate db_connections.json → connections table."""
    path = os.path.join(get_data_dir(), "db_connections.json")
    data = _load_json(path, default={"connections": {}})
    connections = data.get("connections", {})

    engine = get_engine()
    migrated, skipped = 0, 0
    if dry_run:
        print(f"  [dry-run] connections: {len(connections)} entries to migrate")
        return len(connections), 0

    with engine.begin() as conn:
        for conn_id, entry in connections.items():
            # Check if already exists
            existing = conn.execute(
                select(connections_table.c.id).where(connections_table.c.id == conn_id)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(insert(connections_table).values(
                id=conn_id,
                name=entry.get("name", ""),
                db_type=entry.get("db_type", ""),
                host=entry.get("host", ""),
                port=entry.get("port", 3306),
                database=entry.get("database", ""),
                username=entry.get("username", ""),
                password=entry.get("password", ""),  # Already Fernet-encrypted
                file_path=entry.get("file_path", ""),
                verified=1 if entry.get("verified", False) else 0,
                created_at=entry.get("created_at", ""),
                updated_at=entry.get("updated_at", ""),
            ))
            migrated += 1
    return migrated, skipped


def migrate_templates(dry_run: bool = False) -> tuple[int, int]:
    """Migrate templates.json → templates table."""
    path = os.path.join(get_data_dir(), "templates.json")
    data = _load_json(path, default={"templates": {}})
    templates = data.get("templates", {})

    engine = get_engine()
    migrated, skipped = 0, 0
    if dry_run:
        print(f"  [dry-run] templates: {len(templates)} entries to migrate")
        return len(templates), 0

    with engine.begin() as conn:
        for tmpl_id, entry in templates.items():
            existing = conn.execute(
                select(templates_table.c.id).where(templates_table.c.id == tmpl_id)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(insert(templates_table).values(
                id=tmpl_id,
                name=entry.get("name", ""),
                description=entry.get("description", ""),
                category=entry.get("category", ""),
                tags=_json_dumps(entry.get("tags", [])),
                author=entry.get("author", ""),
                version=entry.get("version", "1.0"),
                config_state=_json_dumps(entry.get("config_state", {})),
                requirements=_json_dumps(entry.get("requirements", [])),
                usage_count=entry.get("usage_count", 0),
                is_official=1 if entry.get("is_official", False) else 0,
                created_at=entry.get("created_at", ""),
                updated_at=entry.get("updated_at", ""),
            ))
            migrated += 1
    return migrated, skipped


def migrate_users(dry_run: bool = False) -> tuple[int, int]:
    """Migrate users.json → users table."""
    path = os.path.join(get_data_dir(), "users.json")
    data = _load_json(path, default={"users": {}})
    users = data.get("users", {})

    engine = get_engine()
    migrated, skipped = 0, 0
    if dry_run:
        print(f"  [dry-run] users: {len(users)} entries to migrate")
        return len(users), 0

    with engine.begin() as conn:
        for user_id, entry in users.items():
            existing = conn.execute(
                select(users_table.c.id).where(users_table.c.id == user_id)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(insert(users_table).values(
                id=user_id,
                username=entry.get("username", ""),
                role=entry.get("role", "editor"),
                password_hash=entry.get("password_hash", ""),  # Already hashed
                created_at=entry.get("created_at", ""),
                must_change_password=1 if entry.get("must_change_password", False) else 0,
            ))
            migrated += 1
    return migrated, skipped


def migrate_schedules(dry_run: bool = False) -> tuple[int, int]:
    """Migrate schedules.json → schedules table."""
    path = os.path.join(get_data_dir(), "schedules.json")
    data = _load_json(path, default={"schedules": []})
    schedules = data if isinstance(data, list) else data.get("schedules", [])

    engine = get_engine()
    migrated, skipped = 0, 0
    if dry_run:
        print(f"  [dry-run] schedules: {len(schedules)} entries to migrate")
        return len(schedules), 0

    with engine.begin() as conn:
        for entry in schedules:
            sched_id = entry.get("id", "")
            if not sched_id:
                continue
            existing = conn.execute(
                select(schedules_table.c.id).where(schedules_table.c.id == sched_id)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(insert(schedules_table).values(
                id=sched_id,
                config_id=entry.get("config_id", ""),
                cron_expression=entry.get("cron_expression", ""),
                description=entry.get("description", ""),
                retry_count=entry.get("retry_count", 0),
                retry_interval=entry.get("retry_interval", 300),
                enabled=1 if entry.get("enabled", True) else 0,
                created_at=entry.get("created_at", ""),
            ))
            migrated += 1
    return migrated, skipped


def migrate_audit_log(dry_run: bool = False) -> tuple[int, int]:
    """Migrate audit_log.json → audit_log table."""
    path = os.path.join(get_data_dir(), "audit_log.json")
    entries = _load_json(path, default=[])
    if not isinstance(entries, list):
        entries = []

    engine = get_engine()
    migrated = 0
    if dry_run:
        print(f"  [dry-run] audit_log: {len(entries)} entries to migrate")
        return len(entries), 0

    # Audit log uses auto-increment IDs, so we can't easily check for duplicates.
    # We migrate all entries. Running migration twice will duplicate audit entries.
    # To be safe, we only migrate if the audit_log table is empty.
    with engine.begin() as conn:
        from sqlalchemy import func
        count = conn.execute(select(func.count()).select_from(audit_log_table)).scalar()
        if count and count > 0:
            print(f"  audit_log: table already has {count} entries, skipping (use --force to override)")
            return 0, 0

        for entry in entries:
            conn.execute(insert(audit_log_table).values(
                timestamp=entry.get("timestamp", ""),
                action=entry.get("action", ""),
                target_type=entry.get("target_type", ""),
                target_id=entry.get("target_id", ""),
                details=_json_dumps(entry.get("details", {})),
            ))
            migrated += 1
    return migrated, 0


def migrate_settings(kind: str, dry_run: bool = False) -> tuple[int, int]:
    """Migrate smtp_settings.json or ai_settings.json → settings table."""
    filename = f"{kind}_settings.json"
    path = os.path.join(get_data_dir(), filename)
    if not os.path.exists(path):
        if dry_run:
            print(f"  [dry-run] {kind} settings: file not found, skipping")
        return 0, 0

    with open(path) as f:
        data = json.load(f)

    engine = get_engine()
    if dry_run:
        print(f"  [dry-run] {kind} settings: 1 entry to migrate")
        return 1, 0

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    # schema_version is storage metadata, not a model field — don't migrate it
    data.pop("schema_version", None)
    with engine.begin() as conn:
        existing = conn.execute(
            select(settings_table.c.kind).where(settings_table.c.kind == kind)
        ).fetchone()
        if existing:
            return 0, 1

        conn.execute(insert(settings_table).values(
            kind=kind,
            data=_json_dumps(data),  # Secrets already Fernet-encrypted in JSON
            updated_at=now,
        ))
    return 1, 0


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON storage to SQLite (T-5E-02)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--sqlite-path", default=None, help="SQLite database path")
    args = parser.parse_args()

    # Set SQLite path if specified
    if args.sqlite_path:
        os.environ["CONFIGFORGE_SQLITE_PATH"] = args.sqlite_path
        get_engine.cache_clear()

    db_path = get_sqlite_path()
    print("=== JSON → SQLite Migration (T-5E-02) ===")
    print(f"SQLite database: {db_path}")
    print(f"Mode: {'dry-run' if args.dry_run else 'write'}")
    print()

    # Ensure schema exists (creates tables if not exist)
    if not args.dry_run:
        engine = get_engine()
        init_schema(engine)

    total_migrated = 0
    total_skipped = 0

    print("Migrating connections...")
    m, s = migrate_connections(args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating templates...")
    m, s = migrate_templates(args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating users...")
    m, s = migrate_users(args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating schedules...")
    m, s = migrate_schedules(args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating audit_log...")
    m, s = migrate_audit_log(args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating SMTP settings...")
    m, s = migrate_settings("smtp", args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating AI settings...")
    m, s = migrate_settings("ai", args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print()
    print("=== Migration Summary ===")
    print(f"Total migrated: {total_migrated}")
    print(f"Total skipped:  {total_skipped}")
    if not args.dry_run:
        print()
        print("To use SQLite backend, set:")
        print("  CONFIGFORGE_STORAGE_BACKEND=sqlite")
        print(f"  CONFIGFORGE_SQLITE_PATH={db_path}")
        print()
        print("Note: Pipeline configs (configs/) are NOT migrated — they remain in JSON.")
        print("Note: BackgroundScheduler integration requires T-5E-04.")


if __name__ == "__main__":
    main()
