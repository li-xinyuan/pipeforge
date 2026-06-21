"""Schema versioning and migration framework for ConfigForge data files."""

import json
import logging
import os
import shutil
from datetime import datetime, timezone

from configforge.utils.file_lock import read_json_locked, write_json_locked

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

INDEX_SCHEMA_VERSION = 2


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
    if isinstance(data, dict) and data.get("schema_version", 0) != original_version:
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


# ─── Index migration (v1 → v2) ───

def migrate_index_v1_to_v2(dry_run: bool = False) -> dict:
    """Migrate index.json from v1 (plain list) to v2 (dict with schema_version).

    Reads all state.json files to extract tags and input_types fields,
    then upgrades the index.json structure.

    Args:
        dry_run: If True, only report what would be done without making changes.

    Returns:
        A dict with migration status information.
    """
    from configforge.utils.paths import get_configs_dir

    configs_dir = get_configs_dir()
    index_path = os.path.join(configs_dir, "index.json")

    result = {
        "dry_run": dry_run,
        "migrated": False,
        "configs_updated": 0,
        "errors": [],
    }

    # Check if index.json exists
    if not os.path.exists(index_path):
        result["message"] = "index.json does not exist, nothing to migrate"
        return result

    # Read current index
    try:
        with open(index_path, encoding="utf-8") as f:
            index_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        result["errors"].append(f"Failed to read index.json: {e}")
        return result

    # Determine current schema version
    if isinstance(index_data, dict):
        current_version = index_data.get("schema_version", 1)
        configs = index_data.get("configs", [])
    else:
        # v1 format: plain list
        current_version = 1
        configs = index_data

    # Already at v2 or higher
    if current_version >= INDEX_SCHEMA_VERSION:
        result["message"] = f"index.json already at schema_version {current_version}, no migration needed"
        return result

    # Migrate each config entry by reading state.json for missing fields
    updated_count = 0
    for entry in configs:
        config_id = entry.get("id", "")
        if not config_id:
            continue

        # Check if entry already has v2 fields
        has_tags = "tags" in entry
        has_input_types = "input_types" in entry

        if has_tags and has_input_types:
            continue

        # Read state.json to extract missing fields
        state_path = os.path.join(configs_dir, f"{config_id}.state.json")
        if not os.path.exists(state_path):
            # Try to set defaults
            if not has_tags:
                entry["tags"] = []
            if not has_input_types:
                entry["input_types"] = []
            updated_count += 1
            continue

        try:
            with open(state_path, encoding="utf-8") as sf:
                state = json.load(sf)

            # Extract tags from scene
            if not has_tags:
                scene = state.get("scene", {})
                entry["tags"] = scene.get("tags", [])

            # Extract input_types from inputs
            if not has_input_types:
                inputs = state.get("inputs", [])
                seen = set()
                input_types = []
                for inp in inputs:
                    plugin = inp.get("plugin", "")
                    if plugin and plugin not in seen:
                        seen.add(plugin)
                        input_types.append(plugin)
                entry["input_types"] = input_types

            updated_count += 1
        except (OSError, json.JSONDecodeError) as e:
            result["errors"].append(f"Failed to read {config_id}.state.json: {e}")
            # Set defaults on failure
            if not has_tags:
                entry["tags"] = []
            if not has_input_types:
                entry["input_types"] = []

    if dry_run:
        result["migrated"] = False
        result["configs_updated"] = updated_count
        result["message"] = f"Would migrate {updated_count} config entries to schema_version {INDEX_SCHEMA_VERSION}"
        return result

    # Backup index.json before writing
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = os.path.join(configs_dir, f"index.json.bak.{timestamp}")
    try:
        shutil.copy2(index_path, backup_path)
        logger.info("Backed up index.json to %s", backup_path)
    except OSError as e:
        result["errors"].append(f"Failed to backup index.json: {e}")
        return result

    # Write new v2 format
    new_index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "configs": configs,
    }

    try:
        write_json_locked(index_path, new_index)
        result["migrated"] = True
        result["configs_updated"] = updated_count
        result["message"] = f"Successfully migrated {updated_count} config entries to schema_version {INDEX_SCHEMA_VERSION}"
        logger.info("Migrated index.json to schema_version %d", INDEX_SCHEMA_VERSION)
    except Exception as e:
        # Restore from backup on failure
        result["errors"].append(f"Failed to write new index.json: {e}")
        try:
            shutil.copy2(backup_path, index_path)
            result["errors"].append("Restored index.json from backup")
            logger.error("Failed to write index.json, restored from backup")
        except OSError as restore_err:
            result["errors"].append(f"Failed to restore from backup: {restore_err}")
            logger.critical("Failed to restore index.json from backup: %s", restore_err)

    return result
