"""Data backup and restore utilities for ConfigForge.

Creates zip archives of the data/ and configs/ directories.
Supports scheduled backups with retention policy.
"""

import io
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from configforge.utils.paths import get_configs_dir, get_data_dir


def _get_backup_dir() -> str:
    """Return the backup directory path, creating it if needed."""
    backup_dir = os.path.join(get_data_dir(), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def create_backup() -> tuple[str, bytes]:
    """Create a zip backup of configs/ and data/ directories.

    Returns (filename, zip_bytes).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"configforge_backup_{timestamp}.zip"

    buf = io.BytesIO()
    configs_dir = get_configs_dir()
    data_dir = get_data_dir()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add configs directory
        if os.path.isdir(configs_dir):
            for root, _dirs, files in os.walk(configs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(configs_dir))
                    zf.write(file_path, arcname)

        # Add data directory (excluding backups to avoid recursion)
        if os.path.isdir(data_dir):
            backup_dir_abs = os.path.join(data_dir, "backups")
            for root, _dirs, files in os.walk(data_dir):
                # Skip the backups directory itself
                if os.path.abspath(root).startswith(os.path.abspath(backup_dir_abs)):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(data_dir))
                    zf.write(file_path, arcname)

        # Add metadata
        zf.writestr("_backup_meta.json", f'{{"created_at": "{timestamp}", "version": "0.8.1"}}')

    return filename, buf.getvalue()


def restore_backup(zip_bytes: bytes) -> dict:
    """Restore data from a zip backup.

    Returns a summary dict with restored file count.
    """
    configs_dir = get_configs_dir()
    data_dir = get_data_dir()

    # Create dirs if they don't exist
    os.makedirs(configs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    restored_files = 0
    errors = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for info in zf.infolist():
            if info.filename.startswith("_"):
                continue  # Skip metadata files

            # Determine target: configs/ or data/
            parts = info.filename.split("/", 1)
            if len(parts) < 2:
                continue

            top_dir, rel_path = parts[0], parts[1]
            if top_dir == "configs":
                target_path = os.path.join(configs_dir, rel_path)
            elif top_dir == "data":
                target_path = os.path.join(data_dir, rel_path)
            else:
                continue

            # Skip backups directory on restore
            if "/backups/" in target_path or target_path.endswith("/backups"):
                continue

            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(zf.read(info.filename))
                restored_files += 1
            except Exception as e:
                errors.append(f"Failed to restore {info.filename}: {e}")

    return {"restored_files": restored_files, "errors": errors}


def list_backups() -> list[dict]:
    """List available backup files with metadata."""
    backup_dir = _get_backup_dir()
    backups = []
    if not os.path.isdir(backup_dir):
        return backups

    for filename in sorted(os.listdir(backup_dir), reverse=True):
        if not filename.endswith(".zip"):
            continue
        filepath = os.path.join(backup_dir, filename)
        stat = os.stat(filepath)
        backups.append({
            "filename": filename,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return backups


def cleanup_old_backups(keep_count: int = 7) -> int:
    """Remove old backups, keeping only the most recent `keep_count`.

    Returns the number of deleted backups.
    """
    backup_dir = _get_backup_dir()
    if not os.path.isdir(backup_dir):
        return 0

    files = []
    for f in os.listdir(backup_dir):
        if f.endswith(".zip"):
            filepath = os.path.join(backup_dir, f)
            files.append((filepath, os.path.getmtime(filepath)))

    # Sort by mtime descending
    files.sort(key=lambda x: x[1], reverse=True)

    deleted = 0
    for filepath, _ in files[keep_count:]:
        try:
            os.remove(filepath)
            deleted += 1
        except OSError:
            pass

    return deleted


def save_backup_to_disk(zip_bytes: bytes, filename: str) -> str:
    """Save backup bytes to the backups directory. Returns the file path."""
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    with open(filepath, "wb") as f:
        f.write(zip_bytes)
    # Cleanup old backups after saving
    cleanup_old_backups()
    return filepath
