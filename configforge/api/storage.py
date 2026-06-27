"""存储后端信息 API (T-5E-03)。

提供只读端点返回当前存储后端类型和配置摘要，供前端 Settings 页面展示。
不在 import 时绑定 store，直接读取环境变量和引擎信息，避免运行时切换问题。
"""
from __future__ import annotations

import os
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends

from configforge.middleware.auth import require_role
from configforge.models.user import User

router = APIRouter(tags=["存储后端"])

# 后端类型中文描述
_BACKEND_DESCRIPTIONS = {
    "json": "JSON 文件存储（默认）— 单机部署，零运维",
    "sqlite": "SQLite 数据库 — 单机生产，结构化查询",
    "postgresql": "PostgreSQL 数据库 — 多实例/高并发生产环境",
}


def _mask_database_url(url: str) -> str:
    """脱敏 PostgreSQL 连接字符串，隐藏密码。"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.password:
            # 用 *** 替换密码
            masked_netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                masked_netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=masked_netloc))
        return url
    except Exception:
        # 解析失败时返回协议+host，隐藏其余部分
        return url.split("@")[-1] if "@" in url else "***"


@router.get(
    "/api/storage-backend",
    summary="获取当前存储后端信息",
    description="返回当前存储后端类型、配置摘要和表列表（只读，需 admin 权限）。",
)
async def get_storage_backend_info(_user: User = Depends(require_role("admin"))):
    """返回当前存储后端的只读信息。"""
    backend = os.environ.get("CONFIGFORGE_STORAGE_BACKEND", "json").lower()
    database_url = os.environ.get("CONFIGFORGE_DATABASE_URL", "")

    # 获取引擎方言和表信息
    dialect = None
    table_count = None
    try:
        from configforge.storage.sql_schema import get_engine, metadata
        engine = get_engine()
        dialect = engine.dialect.name
        table_count = len(metadata.tables)
    except Exception:
        # JSON 后端无 SQL 引擎
        pass

    # 构建配置摘要
    config_summary = {}
    if backend == "json":
        from configforge.utils.paths import get_data_dir
        config_summary["data_dir"] = get_data_dir()
    elif backend == "sqlite":
        from configforge.storage.sql_schema import get_sqlite_path
        config_summary["sqlite_path"] = get_sqlite_path()
    elif backend == "postgresql":
        config_summary["database_url_masked"] = _mask_database_url(database_url)

    return {
        "backend": backend,
        "description": _BACKEND_DESCRIPTIONS.get(backend, backend),
        "dialect": dialect,
        "table_count": table_count,
        "config": config_summary,
        # 切换指引
        "switch_hint": "修改环境变量 CONFIGFORGE_STORAGE_BACKEND 并重启服务。详见 docs/DEPLOYMENT.md「存储后端选择」。",
    }
