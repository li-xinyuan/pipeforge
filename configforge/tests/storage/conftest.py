"""Pytest fixtures for SQLite storage backend tests (T-5E-02).

每个测试使用独立的临时 SQLite 数据库，避免相互污染。
通过环境变量 CONFIGFORGE_STORAGE_BACKEND=sqlite 切换后端，
并在测试结束后清理 lru_cache 和环境变量，确保测试隔离。
"""
from __future__ import annotations

import os
import shutil
from collections.abc import Iterator

import pytest


@pytest.fixture
def sqlite_env(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """配置 SQLite 后端环境：临时 data_dir + 临时 DB 路径。

    Yields dict with paths for inspection. Cleans up lru_cache and env vars on exit.
    """
    data_dir = str(tmp_path / "data")
    db_path = str(tmp_path / "test.db")
    os.makedirs(data_dir, exist_ok=True)

    # Set env vars BEFORE importing storage modules
    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", data_dir)
    monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("CONFIGFORGE_SQLITE_PATH", db_path)

    # Clear all lru_cache in storage layer so they pick up new env
    from configforge.storage import (
        get_audit_store,
        get_connection_store,
        get_schedule_store,
        get_template_store,
        get_user_store,
    )
    from configforge.storage.sqlite_schema import get_engine

    get_engine.cache_clear()
    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()

    yield {"data_dir": data_dir, "db_path": db_path}

    # Cleanup: clear caches so they don't leak to other tests
    get_engine.cache_clear()
    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()

    # Remove WAL/SHM files if any
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture
def json_env(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """配置 JSON 后端环境（用于对比测试和后端切换测试）。"""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)

    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", data_dir)
    monkeypatch.setenv("CONFIGFORGE_STORAGE_BACKEND", "json")
    monkeypatch.delenv("CONFIGFORGE_SQLITE_PATH", raising=False)

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

    yield {"data_dir": data_dir}

    get_connection_store.cache_clear()
    get_template_store.cache_clear()
    get_user_store.cache_clear()
    get_audit_store.cache_clear()
    get_schedule_store.cache_clear()
