"""Schema versioning and migration framework for ConfigForge data files."""

import json
import logging
import os

from configforge.utils.file_lock import read_json_locked, write_json_locked

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


def ensure_schema_version(data: dict, file_path: str) -> dict:
    """Ensure data has a schema_version field and migrate if needed.

    Args:
        data: The loaded JSON data dict.
        file_path: Path to the data file (for logging).

    Returns:
        The (possibly migrated) data dict with schema_version set.
    """
    # If data is a list (e.g. index.json, notifications.json), wrap it in a dict
    # for migration purposes, then unwrap it back.
    is_list = isinstance(data, list)
    if is_list:
        data = {"_items": data}

    version = data.get("schema_version", 0)

    if version == CURRENT_SCHEMA_VERSION:
        if is_list:
            return data["_items"]
        return data

    if version > CURRENT_SCHEMA_VERSION:
        logger.warning(
            "Data file %s has schema_version %d, newer than current %d. "
            "Some features may not work correctly.",
            file_path, version, CURRENT_SCHEMA_VERSION,
        )
        if is_list:
            return data["_items"]
        return data

    # Run migrations sequentially
    for migrate_fn in _MIGRATIONS[version:]:
        logger.info("Migrating %s from schema_version %d", file_path, version)
        data = migrate_fn(data)
        version += 1

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    logger.info("Migrated %s to schema_version %d", file_path, CURRENT_SCHEMA_VERSION)

    if is_list:
        return data["_items"]
    return data


def load_with_migration(file_path: str, default: dict | list | None = None) -> dict | list:
    """Load a JSON file with automatic schema migration.

    Args:
        file_path: Path to the JSON file.
        default: Default data if file doesn't exist (dict or list).

    Returns:
        The loaded and possibly migrated data (dict or list).
    """
    if not os.path.exists(file_path):
        data = default if default is not None else {}
        if isinstance(data, dict) and data and "schema_version" not in data:
            data["schema_version"] = CURRENT_SCHEMA_VERSION
        return data

    raw = read_json_locked(file_path)
    original_version = raw.get("schema_version", 0) if isinstance(raw, dict) else 0
    data = ensure_schema_version(raw, file_path)

    # Save back if migration happened
    if isinstance(data, dict):
        if data.get("schema_version", 0) != original_version:
            write_json_locked(file_path, data)

    return data


# ─── Migration functions ───
# Each function migrates from version N to version N+1.
# _MIGRATIONS[0] migrates from v0 → v1, etc.

def _migrate_v0_to_v1(data: dict) -> dict:
    """Initial schema version — add schema_version field.

    Also handles the legacy 'processor' → 'processors' migration for config state files.
    """
    # Migrate single processor to processors list (legacy config format)
    if "processor" in data:
        if not data.get("processors"):
            proc = data.pop("processor")
            if isinstance(proc, dict):
                if "outputTable" in proc:
                    proc["output_tables"] = [proc.pop("outputTable")]
                data["processors"] = [proc]
        else:
            data.pop("processor")

    return data


_MIGRATIONS = [
    _migrate_v0_to_v1,
]
