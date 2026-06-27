"""通用 SQL 存储后端 — Schema 定义与引擎管理 (T-5E-03)。

使用 SQLAlchemy 2.0 Core 风格 API（Table 定义 + select/insert/update/delete）。
支持 SQLite 和 PostgreSQL 两种后端，通过环境变量切换：

- SQLite（默认）：CONFIGFORGE_STORAGE_BACKEND=sqlite, CONFIGFORGE_SQLITE_PATH=<path>
- PostgreSQL：CONFIGFORGE_STORAGE_BACKEND=postgresql, CONFIGFORGE_DATABASE_URL=postgresql://...

SQLite 启用 WAL 模式支持并发读；PostgreSQL 使用连接池。
Schema 定义使用通用类型（String/Integer/Text），SQLAlchemy 自动处理方言差异。
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine

from configforge.utils.paths import get_data_dir

# ---------------------------------------------------------------------------
# 数据库路径 / URL
# ---------------------------------------------------------------------------


def _default_db_path() -> str:
    return os.path.join(get_data_dir(), "configforge.db")


def get_sqlite_path() -> str:
    """获取 SQLite 数据库文件路径。"""
    return os.environ.get("CONFIGFORGE_SQLITE_PATH", _default_db_path())


def get_database_url() -> str:
    """获取数据库连接 URL。

    优先级：
    1. CONFIGFORGE_DATABASE_URL 环境变量（PostgreSQL 等）
    2. 根据 CONFIGFORGE_STORAGE_BACKEND 构造 SQLite URL

    对于 PostgreSQL，URL 格式如：
        postgresql://user:password@host:5432/dbname
        postgresql+psycopg2://user:password@host:5432/dbname
    """
    # If DATABASE_URL is set, use it directly (supports any SQLAlchemy URL)
    url = os.environ.get("CONFIGFORGE_DATABASE_URL")
    if url:
        return url

    # Otherwise, construct SQLite URL from path
    return f"sqlite:///{get_sqlite_path()}"


def _get_backend() -> str:
    """获取当前存储后端名称。"""
    return os.environ.get("CONFIGFORGE_STORAGE_BACKEND", "json").lower()


# ---------------------------------------------------------------------------
# 引擎管理
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """创建并缓存数据库引擎。

    根据后端类型创建合适的引擎：
    - SQLite：WAL 模式 + check_same_thread=False
    - PostgreSQL：连接池 + pool_pre_ping
    """
    url = get_database_url()
    backend = _get_backend()
    is_sqlite = url.startswith("sqlite") or backend == "sqlite"

    if is_sqlite:
        db_path = get_sqlite_path()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_pre_ping=True,
        )
        # SQLite 特有 PRAGMA：WAL 模式 + 外键约束
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
    else:
        # PostgreSQL 或其他数据库
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,  # 1 小时回收连接，避免数据库端超时
        )

    # 初始化表结构
    init_schema(engine)

    return engine


# ---------------------------------------------------------------------------
# Schema 定义
# ---------------------------------------------------------------------------

metadata = MetaData()

connections_table = Table(
    "connections",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("db_type", String(32), nullable=False),
    Column("host", String(255), default=""),
    Column("port", Integer, default=3306),
    Column("database", String(255), default=""),
    Column("username", String(255), default=""),
    Column("password", String(512), default=""),  # Fernet 加密
    Column("file_path", String(512), default=""),
    Column("verified", Integer, default=0),  # 0/1 boolean
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

templates_table = Table(
    "templates",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", String(1024), default=""),
    Column("category", String(64), default=""),
    Column("tags", String(2048), default="[]"),  # JSON array
    Column("author", String(255), default=""),
    Column("version", String(32), default="1.0"),
    Column("config_state", String(65535), default="{}"),  # JSON
    Column("requirements", String(8192), default="[]"),  # JSON array
    Column("usage_count", Integer, default=0),
    Column("is_official", Integer, default=0),  # 0/1 boolean
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

users_table = Table(
    "users",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("username", String(128), nullable=False, unique=True),
    Column("role", String(32), nullable=False, default="editor"),
    Column("password_hash", String(512), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("must_change_password", Integer, default=0),  # 0/1 boolean
)

schedules_table = Table(
    "schedules",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("config_id", String(64), nullable=False),
    Column("cron_expression", String(128), nullable=False),
    Column("description", String(512), default=""),
    Column("retry_count", Integer, default=0),
    Column("retry_interval", Integer, default=300),
    Column("enabled", Integer, default=1),  # 0/1 boolean
    Column("created_at", String(40), nullable=False),
    Column("last_run_at", String(40), default=""),  # T-5E-04: 上次执行时间
    Column("last_run_status", String(32), default=""),  # T-5E-04: "success" | "failed"
)

audit_log_table = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String(40), nullable=False),
    Column("action", String(32), nullable=False),
    Column("target_type", String(64), nullable=False),
    Column("target_id", String(128), nullable=False),
    Column("details", String(8192), default="{}"),  # JSON
)

settings_table = Table(
    "settings",
    metadata,
    Column("kind", String(32), primary_key=True),  # 'smtp' / 'ai'
    Column("data", String(8192), nullable=False),  # JSON with encrypted secrets
    Column("updated_at", String(40), nullable=False),
)

rate_limit_table = Table(
    "rate_limit_entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("key", String(255), nullable=False, index=True),
    Column("timestamp", Float, nullable=False),
)


def init_schema(engine: Engine) -> None:
    """创建所有表（如果不存在），并执行 schema 迁移。"""
    metadata.create_all(engine)
    _migrate_schedule_columns(engine)


def _migrate_schedule_columns(engine: Engine) -> None:
    """T-5E-04 迁移：为 schedules 表添加 last_run_at / last_run_status 列。

    ALTER TABLE ADD COLUMN 在 SQLite 和 PostgreSQL 上都支持。
    对于新建的数据库，create_all 已包含新列，此函数只处理已有数据库。
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "schedules" not in insp.get_table_names():
        return
    existing = {col["name"] for col in insp.get_columns("schedules")}
    with engine.begin() as conn:
        if "last_run_at" not in existing:
            conn.execute(text("ALTER TABLE schedules ADD COLUMN last_run_at TEXT"))
        if "last_run_status" not in existing:
            conn.execute(text("ALTER TABLE schedules ADD COLUMN last_run_status TEXT"))


def drop_all(engine: Engine) -> None:
    """删除所有表（用于测试清理）。"""
    metadata.drop_all(engine)
