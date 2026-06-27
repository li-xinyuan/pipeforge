"""SQLite → PostgreSQL 数据迁移脚本 (T-5E-03)。

将 SQLite 数据库中的数据迁移到 PostgreSQL。
加密字段（密码、API key）在 SQLite 中已 Fernet 加密，可直接复制到 PostgreSQL，无需重新加密。
用户密码哈希同样可直接复制。

用法：
    python -m configforge.utils.migrate_to_postgres \\
        --sqlite-path data/configforge.db \\
        --database-url "postgresql://user:pass@host:5432/configforge" \\
        [--dry-run]

选项：
    --sqlite-path   源 SQLite 数据库路径（默认 data/configforge.db）
    --database-url  目标 PostgreSQL 连接字符串
                    （也可通过 CONFIGFORGE_DATABASE_URL 环境变量提供）
    --dry-run       只打印迁移计划，不实际写入

注意：
- 迁移是幂等的：重复运行会跳过已存在的记录（audit_log 除外，见下）
- Configs（pipeline 配置）仍使用 JSON 文件存储，不在此次迁移范围内
- audit_log 使用自增 ID，无法按内容去重；仅在目标表为空时迁移，避免重复
- 迁移后需设置 CONFIGFORGE_STORAGE_BACKEND=postgresql 才能使用 PostgreSQL 后端
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.engine import Engine

from configforge.storage.sql_schema import (
    audit_log_table,
    connections_table,
    metadata,
    schedules_table,
    settings_table,
    templates_table,
    users_table,
)
from configforge.utils.paths import get_data_dir


def _default_sqlite_path() -> str:
    return os.environ.get("CONFIGFORGE_SQLITE_PATH", os.path.join(get_data_dir(), "configforge.db"))


def _create_sqlite_engine(sqlite_path: str) -> Engine:
    """创建源 SQLite 引擎（只读访问）。"""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    return create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )


def _create_postgres_engine(database_url: str) -> Engine:
    """创建目标 PostgreSQL 引擎，并初始化 schema。"""
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )
    # 初始化表结构（如果不存在）
    metadata.create_all(engine)
    return engine


def _table_exists(src_engine: Engine, table) -> bool:
    """检查 SQLite 源中表是否存在（避免迁移空 DB 报错）。"""
    from sqlalchemy import inspect
    inspector = inspect(src_engine)
    return table.name in inspector.get_table_names()


def migrate_connections(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """connections: SQLite → PostgreSQL。"""
    if not _table_exists(src, connections_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(connections_table)).fetchall()
    migrated, skipped = 0, 0
    if dry_run:
        return len(rows), 0
    with dst.begin() as conn:
        for r in rows:
            row = dict(r._mapping)
            existing = conn.execute(
                select(connections_table.c.id).where(connections_table.c.id == row["id"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(insert(connections_table).values(**row))
            migrated += 1
    return migrated, skipped


def migrate_templates(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """templates: SQLite → PostgreSQL。"""
    if not _table_exists(src, templates_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(templates_table)).fetchall()
    migrated, skipped = 0, 0
    if dry_run:
        return len(rows), 0
    with dst.begin() as conn:
        for r in rows:
            row = dict(r._mapping)
            existing = conn.execute(
                select(templates_table.c.id).where(templates_table.c.id == row["id"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(insert(templates_table).values(**row))
            migrated += 1
    return migrated, skipped


def migrate_users(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """users: SQLite → PostgreSQL。"""
    if not _table_exists(src, users_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(users_table)).fetchall()
    migrated, skipped = 0, 0
    if dry_run:
        return len(rows), 0
    with dst.begin() as conn:
        for r in rows:
            row = dict(r._mapping)
            existing = conn.execute(
                select(users_table.c.id).where(users_table.c.id == row["id"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(insert(users_table).values(**row))
            migrated += 1
    return migrated, skipped


def migrate_schedules(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """schedules: SQLite → PostgreSQL。"""
    if not _table_exists(src, schedules_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(schedules_table)).fetchall()
    migrated, skipped = 0, 0
    if dry_run:
        return len(rows), 0
    with dst.begin() as conn:
        for r in rows:
            row = dict(r._mapping)
            existing = conn.execute(
                select(schedules_table.c.id).where(schedules_table.c.id == row["id"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(insert(schedules_table).values(**row))
            migrated += 1
    return migrated, skipped


def migrate_audit_log(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """audit_log: SQLite → PostgreSQL。

    audit_log 使用自增 ID，无法按内容去重。仅在目标表为空时迁移，避免重复。
    """
    if not _table_exists(src, audit_log_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(audit_log_table)).fetchall()
    if dry_run:
        return len(rows), 0

    with dst.begin() as conn:
        # 仅在目标表为空时迁移
        count = conn.execute(select(func.count()).select_from(audit_log_table)).scalar()
        if count and count > 0:
            print(f"  audit_log: target table already has {count} entries, skipping "
                  "(audit_log uses auto-increment IDs, cannot deduplicate)")
            return 0, 0

        for r in rows:
            row = dict(r._mapping)
            # 不复制自增 ID，让 PostgreSQL 自动分配
            row.pop("id", None)
            conn.execute(insert(audit_log_table).values(**row))
    return len(rows), 0


def migrate_settings(src: Engine, dst: Engine, dry_run: bool = False) -> tuple[int, int]:
    """settings (SMTP/AI): SQLite → PostgreSQL。"""
    if not _table_exists(src, settings_table):
        return 0, 0
    with src.connect() as src_conn:
        rows = src_conn.execute(select(settings_table)).fetchall()
    migrated, skipped = 0, 0
    if dry_run:
        return len(rows), 0
    with dst.begin() as conn:
        for r in rows:
            row = dict(r._mapping)
            existing = conn.execute(
                select(settings_table.c.kind).where(settings_table.c.kind == row["kind"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(insert(settings_table).values(**row))
            migrated += 1
    return migrated, skipped


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite storage to PostgreSQL (T-5E-03)")
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Source SQLite database path (default: data/configforge.db or CONFIGFORGE_SQLITE_PATH)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Target PostgreSQL URL (default: CONFIGFORGE_DATABASE_URL env var)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    sqlite_path = args.sqlite_path or _default_sqlite_path()
    database_url = args.database_url or os.environ.get("CONFIGFORGE_DATABASE_URL")

    if not database_url:
        print("ERROR: PostgreSQL URL is required.")
        print("Provide via --database-url or CONFIGFORGE_DATABASE_URL environment variable.")
        print('Example: postgresql://user:password@host:5432/dbname')
        sys.exit(1)

    if not database_url.startswith("postgresql"):
        print(f"ERROR: --database-url must be a PostgreSQL URL, got: {database_url}")
        sys.exit(1)

    print("=== SQLite → PostgreSQL Migration (T-5E-03) ===")
    print(f"Source SQLite:  {sqlite_path}")
    print(f"Target Postgres: {database_url}")
    print(f"Mode: {'dry-run' if args.dry_run else 'write'}")
    print()

    # Create engines
    try:
        src_engine = _create_sqlite_engine(sqlite_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    dst_engine = _create_postgres_engine(database_url)

    total_migrated = 0
    total_skipped = 0

    print("Migrating connections...")
    m, s = migrate_connections(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating templates...")
    m, s = migrate_templates(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating users...")
    m, s = migrate_users(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating schedules...")
    m, s = migrate_schedules(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating audit_log...")
    m, s = migrate_audit_log(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print("Migrating settings (SMTP/AI)...")
    m, s = migrate_settings(src_engine, dst_engine, args.dry_run)
    total_migrated += m
    total_skipped += s
    print(f"  migrated: {m}, skipped: {s}")

    print()
    print("=== Migration Summary ===")
    print(f"Total migrated: {total_migrated}")
    print(f"Total skipped:  {total_skipped}")
    if not args.dry_run:
        print()
        print("To use PostgreSQL backend, set:")
        print('  CONFIGFORGE_STORAGE_BACKEND=postgresql')
        print(f'  CONFIGFORGE_DATABASE_URL="{database_url}"')
        print()
        print("Note: Pipeline configs (configs/) are NOT migrated — they remain in JSON.")
        print("Note: BackgroundScheduler integration requires T-5E-04.")

    src_engine.dispose()
    dst_engine.dispose()


if __name__ == "__main__":
    main()
