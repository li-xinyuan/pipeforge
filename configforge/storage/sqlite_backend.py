"""SQLite 存储后端实现（向后兼容 shim）。

T-5E-03 起，通用 SQL 后端实现已迁移至 `configforge.storage.sql_backend`，
本模块仅作为向后兼容 shim re-export 所有 Store 类。

现有代码 `from configforge.storage.sqlite_backend import SqliteConnectionStore` 无需修改即可继续工作。
新代码应优先使用 `from configforge.storage.sql_backend import ...`。

实现本身是方言无关的：通过 `sql_schema.get_engine()` 自动适配 SQLite / PostgreSQL。
类名保留 `Sqlite*Store` 前缀以保持向后兼容，但实际支持所有 SQL 后端。
"""

from __future__ import annotations

from configforge.storage.sql_backend import (
    SqliteAuditStore,
    SqliteConnectionStore,
    SqliteScheduleStore,
    SqliteSettingsStore,
    SqliteTemplateStore,
    SqliteUserStore,
)

__all__ = [
    "SqliteAuditStore",
    "SqliteConnectionStore",
    "SqliteScheduleStore",
    "SqliteSettingsStore",
    "SqliteTemplateStore",
    "SqliteUserStore",
]
