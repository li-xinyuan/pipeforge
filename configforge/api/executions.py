"""Execution history API."""
import os
import json
import shutil
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from configforge.models.wizard import ExecutionRecord, ErrorResponse
from configforge.utils.security import validate_id
from configforge.utils.file_lock import read_json_locked, write_json_locked

router = APIRouter(prefix="/api/executions", tags=["executions"])

DATA_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
EXEC_DIR = os.path.join(DATA_DIR, "executions")
EXEC_INDEX = os.path.join(EXEC_DIR, "index.json")
MAX_OUTPUT_FILES = 50  # Keep last 50 output files


def _cleanup_old_outputs():
    """Remove output files beyond MAX_OUTPUT_FILES limit."""
    if not os.path.exists(EXEC_DIR):
        return
    dirs = sorted(
        [d for d in os.listdir(EXEC_DIR) if os.path.isdir(os.path.join(EXEC_DIR, d))],
        reverse=True
    )
    for d in dirs[MAX_OUTPUT_FILES:]:
        shutil.rmtree(os.path.join(EXEC_DIR, d), ignore_errors=True)


def _sanitize_summary(summary: list[dict]) -> list[dict]:
    """Mask sensitive fields (connection strings, passwords) in execution summaries."""
    import re
    sanitized = []
    for item in summary:
        s = dict(item)
        for key in list(s.keys()):
            val = str(s[key]) if s[key] is not None else ""
            # Mask connection strings like mysql://user:pass@host/db
            if re.search(r"://.*@", val):
                s[key] = re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", val)
        sanitized.append(s)
    return sanitized


def _update_exec_index(record: ExecutionRecord):
    """Add or update an execution entry in the index file."""
    os.makedirs(EXEC_DIR, exist_ok=True)
    index = []
    if os.path.exists(EXEC_INDEX):
        index = read_json_locked(EXEC_INDEX)
    index.insert(0, {
        "id": record.id,
        "config_id": record.config_id,
        "config_version": record.config_version,
        "scene_name": record.scene_name,
        "status": record.status,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "duration_ms": record.duration_ms,
        "inputs_summary": record.inputs_summary,
        "processors_summary": record.processors_summary,
        "output_type": record.output_type,
        "checks_summary": record.checks_summary,
        "error_message": record.error_message,
        "output_file_name": record.output_file_name,
        "diagnosis": record.diagnosis,
    })
    # Keep last 100 entries
    write_json_locked(EXEC_INDEX, index[:100])

    # Clean up old output directories
    _cleanup_old_outputs()


def _save_failed_execution(
    exec_id: str,
    started_at: str,
    config_id: str,
    config_version: int | None,
    scene_name: str,
    inputs_summary: list[dict],
    processors_summary: list[dict],
    output_type: str,
    error_message: str,
    checks_summary: list[dict] | None = None,
    diagnosis: dict | None = None,
):
    """Persist a failed execution record."""
    finished_at = datetime.now(UTC).isoformat()
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)

    record = ExecutionRecord(
        id=exec_id,
        config_id=config_id,
        config_version=config_version,
        scene_name=scene_name,
        status="failed",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        inputs_summary=_sanitize_summary(inputs_summary),
        processors_summary=processors_summary,
        output_type=output_type,
        checks_summary=checks_summary or [],
        error_message=error_message,
        output_file_name=None,
        diagnosis=diagnosis,
    )

    os.makedirs(os.path.join(EXEC_DIR, exec_id), exist_ok=True)
    result_path = os.path.join(EXEC_DIR, exec_id, "result.json")
    with open(result_path, "w") as f:
        json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

    _update_exec_index(record)


@router.get("")
async def list_executions(
    search: str = None,
    config_id: str = None,
    page: int = 1,
    page_size: int = 10,
):
    """List execution history with optional search and pagination."""
    if not os.path.exists(EXEC_INDEX):
        return {"items": [], "total": 0, "page": page,
                "page_size": page_size, "total_pages": 0}
    index = read_json_locked(EXEC_INDEX)
    if config_id:
        index = [e for e in index if e.get("config_id") == config_id]
    if search:
        q = search.lower()
        index = [e for e in index if q in e.get("scene_name", "").lower()]
    total = len(index)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    items = index[start:start + page_size]
    # Backfill missing fields for old records
    for item in items:
        item.setdefault("finished_at", None)
        item.setdefault("inputs_summary", [])
        item.setdefault("processors_summary", [])
        item.setdefault("output_type", "")
        item.setdefault("checks_summary", [])
        item.setdefault("error_message", None)
        item.setdefault("diagnosis", None)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{exec_id}")
async def get_execution(exec_id: str):
    """Get execution detail."""
    validate_id(exec_id, "exec_id")
    result_path = os.path.join(EXEC_DIR, exec_id, "result.json")
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Execution not found")
    with open(result_path) as f:
        return json.load(f)


@router.get("/{exec_id}/download")
async def download_execution_output(exec_id: str):
    """Download execution output file."""
    validate_id(exec_id, "exec_id")
    result_path = os.path.join(EXEC_DIR, exec_id, "result.json")
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Execution not found")
    with open(result_path) as f:
        record = json.load(f)
    filename = record.get("output_file_name")
    if not filename:
        raise HTTPException(status_code=404, detail="No output file for this execution")
    file_path = os.path.join(EXEC_DIR, exec_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    media_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(file_path, media_type=media_type, filename=filename)


@router.delete("/{exec_id}")
async def delete_execution(exec_id: str):
    """Delete an execution record and its files."""
    validate_id(exec_id, "exec_id")
    exec_dir = os.path.join(EXEC_DIR, exec_id)
    if os.path.exists(exec_dir):
        shutil.rmtree(exec_dir)
    # Update index
    if os.path.exists(EXEC_INDEX):
        index = read_json_locked(EXEC_INDEX)
        index = [e for e in index if e.get("id") != exec_id]
        write_json_locked(EXEC_INDEX, index)
    return {"ok": True}
