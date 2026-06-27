"""Execution history API."""
import json
import os
import shutil
import urllib.parse

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from configforge.models.wizard import ExecutionRecord
from configforge.services.execution_store import (
    DATA_DIR,  # noqa: F401  re-export for backward-compat with tests
    EXEC_DIR,
    EXEC_INDEX,
    MAX_OUTPUT_FILES,  # noqa: F401  re-export
)
from configforge.services.execution_store import (
    cleanup_old_outputs as _cleanup_old_outputs,  # noqa: F401  re-export
)
from configforge.services.execution_store import (
    sanitize_summary as _sanitize_summary,  # noqa: F401  re-export
)
from configforge.services.execution_store import (
    save_failed_execution as _save_failed_execution,  # noqa: F401  re-export
)
from configforge.services.execution_store import (
    update_exec_index as _update_exec_index,  # noqa: F401  re-export
)
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.security import validate_id

router = APIRouter(prefix="/api/executions", tags=["执行历史"])


@router.get("", summary="获取执行历史列表", description="分页获取 Pipeline 执行历史记录。支持按场景名称搜索和按配置 ID 筛选。返回执行状态、耗时、输入输出摘要等信息。")
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


@router.get("/{exec_id}", summary="获取执行详情", description="根据执行 ID 获取单次 Pipeline 执行的详细信息，包括状态、耗时、输入输出摘要、检查点结果和错误信息。", response_model=ExecutionRecord)
async def get_execution(exec_id: str):
    """Get execution detail."""
    validate_id(exec_id, "exec_id")
    result_path = os.path.join(EXEC_DIR, exec_id, "result.json")
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Execution not found")
    with open(result_path) as f:
        return json.load(f)


@router.get("/{exec_id}/download", summary="下载执行输出文件", description="下载指定执行记录的输出文件。支持 Excel (.xlsx) 和 CSV 格式。仅当执行成功且生成了输出文件时可用。")
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
    encoded_name = urllib.parse.quote(filename)
    return FileResponse(file_path, media_type=media_type, filename=filename, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"})


@router.delete("/{exec_id}", summary="删除执行记录", description="删除指定的执行记录及其关联的输出文件。同时从执行索引中移除该记录。")
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
