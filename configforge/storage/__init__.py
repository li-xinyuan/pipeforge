"""存储层包 (T-5E-01 / T-5E-02 / T-5E-03)。

通过环境变量 CONFIGFORGE_STORAGE_BACKEND=json|sqlite|postgresql 切换后端（默认 json）。
提供工厂函数获取各 Store 实例，实现后端可切换。

后端说明：
- json：默认，JSON 文件存储（单机部署）
- sqlite：SQLite 数据库（CONFIGFORGE_SQLITE_PATH 指定路径）
- postgresql：PostgreSQL 数据库（CONFIGFORGE_DATABASE_URL 指定连接字符串）

SQLite 和 PostgreSQL 共用通用 SQL 后端实现（sql_backend.py），
SQLAlchemy Core 根据 URL 自动选择方言。
"""

from __future__ import annotations

import os
from functools import lru_cache

from configforge.storage.base import (
    AuditStoreProtocol,
    ConfigStoreProtocol,
    ConnectionStoreProtocol,
    ScheduleStoreProtocol,
    SettingsStoreProtocol,
    TemplateStoreProtocol,
    UserStoreProtocol,
)
from configforge.storage.json_backend import (
    JsonAuditStore,
    JsonConfigStore,
    JsonConnectionStore,
    JsonScheduleStore,
    JsonSettingsStore,
    JsonTemplateStore,
    JsonUserStore,
)


def _get_backend() -> str:
    """获取当前存储后端名称。"""
    return os.environ.get("CONFIGFORGE_STORAGE_BACKEND", "json").lower()


def _get_sql_class(name: str):
    """懒加载通用 SQL 后端类（避免 JSON 模式下加载 SQLAlchemy）。

    SQLite 和 PostgreSQL 共用同一套 Store 实现（sql_backend.py），
    SQLAlchemy Core 根据 get_engine() 返回的 URL 自动选择方言。
    """
    from configforge.storage import sql_backend
    return getattr(sql_backend, name)


def _validate_postgresql_config() -> None:
    """PostgreSQL 后端前置校验：CONFIGFORGE_DATABASE_URL 必须设置。"""
    if not os.environ.get("CONFIGFORGE_DATABASE_URL"):
        raise RuntimeError(
            "PostgreSQL backend requires CONFIGFORGE_DATABASE_URL environment variable. "
            "Example: postgresql://user:password@host:5432/dbname"
        )


@lru_cache(maxsize=1)
def get_connection_store() -> ConnectionStoreProtocol:
    """获取数据库连接存储实例。"""
    backend = _get_backend()
    if backend == "json":
        return JsonConnectionStore()
    if backend == "sqlite":
        return _get_sql_class("SqliteConnectionStore")()
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteConnectionStore")()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


@lru_cache(maxsize=1)
def get_config_store() -> ConfigStoreProtocol:
    """获取 Pipeline 配置存储实例 (P1-5 落地)。

    JSON 后端返回 JsonConfigStore；SQLite / PostgreSQL 后端暂未实现
    SqliteConfigStore（ConfigStoreProtocol 是 7 个 Protocol 中最后落地的，
    SQL 后端实现留待后续迭代）。
    """
    backend = _get_backend()
    if backend == "json":
        return JsonConfigStore()
    raise NotImplementedError(
        f"Config storage backend '{backend}' is not implemented yet. "
        "Only JSON backend is supported for configs."
    )


@lru_cache(maxsize=1)
def get_template_store() -> TemplateStoreProtocol:
    """获取配置模板存储实例。"""
    backend = _get_backend()
    if backend == "json":
        return JsonTemplateStore()
    if backend == "sqlite":
        return _get_sql_class("SqliteTemplateStore")()
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteTemplateStore")()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


@lru_cache(maxsize=1)
def get_user_store() -> UserStoreProtocol:
    """获取用户存储实例。"""
    backend = _get_backend()
    if backend == "json":
        return JsonUserStore()
    if backend == "sqlite":
        return _get_sql_class("SqliteUserStore")()
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteUserStore")()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


@lru_cache(maxsize=1)
def get_audit_store() -> AuditStoreProtocol:
    """获取审计日志存储实例。"""
    backend = _get_backend()
    if backend == "json":
        return JsonAuditStore()
    if backend == "sqlite":
        return _get_sql_class("SqliteAuditStore")()
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteAuditStore")()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


@lru_cache(maxsize=1)
def get_schedule_store() -> ScheduleStoreProtocol:
    """获取定时调度存储实例。"""
    backend = _get_backend()
    if backend == "json":
        return JsonScheduleStore()
    if backend == "sqlite":
        return _get_sql_class("SqliteScheduleStore")()
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteScheduleStore")()
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


def get_settings_store(kind: str = "smtp") -> SettingsStoreProtocol:
    """获取设置存储实例（SMTP / AI）。

    不使用 lru_cache，因为 kind 参数变化。
    """
    backend = _get_backend()
    if backend == "json":
        return JsonSettingsStore(kind=kind)
    if backend == "sqlite":
        return _get_sql_class("SqliteSettingsStore")(kind=kind)
    if backend == "postgresql":
        _validate_postgresql_config()
        return _get_sql_class("SqliteSettingsStore")(kind=kind)
    raise NotImplementedError(f"Storage backend '{backend}' is not implemented yet")


__all__ = [
    "AuditStoreProtocol",
    "ConfigStoreProtocol",
    "ConnectionStoreProtocol",
    "ScheduleStoreProtocol",
    "SettingsStoreProtocol",
    "TemplateStoreProtocol",
    "UserStoreProtocol",
    "get_audit_store",
    "get_config_store",
    "get_connection_store",
    "get_schedule_store",
    "get_settings_store",
    "get_template_store",
    "get_user_store",
]
