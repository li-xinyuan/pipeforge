"""执行历史持久化层。

从 api/executions.py 抽取的存储逻辑，解除 service→api 反向依赖。
api 层与 service 层均从此模块导入；api 层保留 re-export 以兼容现有测试。
"""
import json
import os
import re
import shutil
from datetime import UTC, datetime

from configforge.models.wizard import ExecutionRecord
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.paths import get_data_dir

DATA_DIR = get_data_dir()
EXEC_DIR = os.path.join(DATA_DIR, "executions")
EXEC_INDEX = os.path.join(EXEC_DIR, "index.json")
MAX_OUTPUT_FILES = 50  # Keep last 50 output files


def cleanup_old_outputs():
    """Remove output files beyond MAX_OUTPUT_FILES limit.

    按修改时间倒序保留最新的 MAX_OUTPUT_FILES 个，删除更早的。
    （此前按目录名排序，会导致新创建但名字排序靠后的目录被误删。）
    """
    if not os.path.exists(EXEC_DIR):
        return
    entries = [
        d for d in os.listdir(EXEC_DIR)
        if os.path.isdir(os.path.join(EXEC_DIR, d))
    ]
    # 按修改时间倒序（最新在前）
    entries.sort(
        key=lambda d: os.path.getmtime(os.path.join(EXEC_DIR, d)),
        reverse=True,
    )
    for d in entries[MAX_OUTPUT_FILES:]:
        shutil.rmtree(os.path.join(EXEC_DIR, d), ignore_errors=True)


def sanitize_summary(summary: list[dict]) -> list[dict]:
    """Mask sensitive fields (connection strings, passwords) in execution summaries."""
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


def update_exec_index(record: ExecutionRecord):
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
    cleanup_old_outputs()


def save_failed_execution(
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
        inputs_summary=sanitize_summary(inputs_summary),
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

    update_exec_index(record)
