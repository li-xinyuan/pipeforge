"""Pipeline 配置存储 (T-5E-01 抽取)。

从 api/configs.py 抽取的存储层逻辑，使存储与 API 层分离。
api/configs.py 改为从此模块 import 这些函数，保持向后兼容。
"""

from __future__ import annotations

import logging
import os

from configforge.utils.cache import TTLCache
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.metrics import configs_total
from configforge.utils.paths import get_configs_dir

logger = logging.getLogger(__name__)

CONFIGS_DIR = get_configs_dir()
os.makedirs(CONFIGS_DIR, exist_ok=True)

INDEX_PATH = os.path.join(CONFIGS_DIR, "index.json")
_cache = TTLCache(ttl=10.0)

INDEX_SCHEMA_VERSION = 2


def _load_index() -> list[dict]:
    """加载配置索引，带 10s TTL 缓存。"""
    cached = _cache.get("index")
    if cached is not None:
        return cached
    if not os.path.exists(INDEX_PATH):
        result: list[dict] = []
        _cache.set("index", result)
        return result
    data = read_json_locked(INDEX_PATH)
    # Support both v1 (plain list) and v2 (dict with schema_version) formats
    if isinstance(data, list):
        result = data
    else:
        result = data.get("configs", [])
    _cache.set("index", result)
    return result


def _save_index(data: list[dict]) -> None:
    """保存配置索引，更新 configs_total 指标。"""
    wrapper = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "configs": data,
    }
    write_json_locked(INDEX_PATH, wrapper)
    _cache.invalidate("index")
    # Update configs_total gauge
    configs_total.set(len(data))


def _read_version_state(config_id: str, version: int) -> dict | None:
    """Read a specific version's state.json. Returns None if not found."""
    # Check versions directory first
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    state_path = os.path.join(versions_dir, f"v{version}.state.json")
    if os.path.exists(state_path):
        return read_json_locked(state_path)

    # Check if this is the current version
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    if entry and entry.get("current_version") == version:
        current_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
        if os.path.exists(current_path):
            return read_json_locked(current_path)

    return None


def _list_version_files(config_id: str) -> list[int]:
    """Return sorted list of version numbers available for a config."""
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    versions: list[int] = []
    if os.path.isdir(versions_dir):
        for filename in os.listdir(versions_dir):
            if filename.startswith("v") and filename.endswith(".state.json"):
                try:
                    v = int(filename[1:].split(".")[0])
                    versions.append(v)
                except ValueError:
                    pass

    # Include current version from index
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    if entry and entry.get("current_version"):
        versions.append(entry["current_version"])

    return sorted(set(versions))
