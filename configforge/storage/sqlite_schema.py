"""SQLite 存储后端 — Schema 定义与引擎管理（向后兼容 shim）。

T-5E-03 起，通用 SQL schema 实现已迁移至 `configforge.storage.sql_schema`，
本模块仅作为向后兼容 shim re-export 所有公共符号。

现有代码 `from configforge.storage.sqlite_schema import ...` 无需修改即可继续工作。
新代码应优先使用 `from configforge.storage.sql_schema import ...`。
"""

from __future__ import annotations

from configforge.storage.sql_schema import (
    connections_table,
    drop_all,
    get_database_url,
    get_engine,
    get_sqlite_path,
    init_schema,
    metadata,
    rate_limit_table,
    schedules_table,
    settings_table,
    templates_table,
    users_table,
    audit_log_table,
)

__all__ = [
    "audit_log_table",
    "connections_table",
    "drop_all",
    "get_database_url",
    "get_engine",
    "get_sqlite_path",
    "init_schema",
    "metadata",
    "rate_limit_table",
    "schedules_table",
    "settings_table",
    "templates_table",
    "users_table",
]
