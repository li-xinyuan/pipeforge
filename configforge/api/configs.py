import fcntl
import json
import os
import shutil
import uuid
from datetime import datetime, UTC

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from configforge.core.pipeline import execute_pipeline
from configforge.models.wizard import (
    ConfigMeta,
    ConfigInputMeta,
    ConfigVersionMeta,
    SaveConfigRequest,
    SaveConfigResponse,
    ExecuteConfigRequest,
    WizardState,
    ErrorResponse,
    ExecutionRecord,
)
from configforge.api.executions import (
    EXEC_DIR,
    _update_exec_index,
    _save_failed_execution,
)
from configforge.services.yaml_builder import build_yaml
from configforge.utils.security import validate_id
from pipeforge.config.exceptions import CheckpointError

router = APIRouter()
logger = logging.getLogger(__name__)

def _migrate_state_dict(state_dict: dict) -> None:
    """Upgrade old format (single processor) to new format (processors list)."""
    if "processor" in state_dict and not state_dict.get("processors"):
        proc = state_dict.pop("processor")
        if "outputTable" in proc:
            proc["output_tables"] = [proc.pop("outputTable")]
        state_dict["processors"] = [proc]


def _validate_config_id(config_id: str) -> str:
    try:
        return validate_id(config_id, "config_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config_id format")


CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
os.makedirs(CONFIGS_DIR, exist_ok=True)

INDEX_PATH = os.path.join(CONFIGS_DIR, "index.json")


def _load_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _save_index(data: list[dict]) -> None:
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@router.get("")
async def list_configs() -> list[ConfigMeta]:
    index = _load_index()
    return [ConfigMeta(**entry) for entry in index]


@router.post("", response_model=SaveConfigResponse)
async def save_config(req: SaveConfigRequest):
    config_id = req.config_id or uuid.uuid4().hex
    now_str = datetime.now(UTC).isoformat()

    # Determine if this is an update or a new config
    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    yaml_path = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
    is_update = os.path.exists(state_path)

    versions_dir = os.path.join(CONFIGS_DIR, config_id)

    if is_update:
        # Load index to get current version and created_at
        index = _load_index()
        old_entry = next((e for e in index if e.get("id") == config_id), None)
        old_version = old_entry.get("current_version", 1) if old_entry else 1
        created_at = old_entry.get("created_at", now_str) if old_entry else now_str

        # Move current files to version directory before overwriting
        os.makedirs(versions_dir, exist_ok=True)
        for suffix in ("state.json", "yaml"):
            current_path = os.path.join(CONFIGS_DIR, f"{config_id}.{suffix}")
            target_path = os.path.join(versions_dir, f"v{old_version}.{suffix}")
            if os.path.exists(current_path):
                shutil.move(current_path, target_path)

        current_version = old_version + 1
    else:
        created_at = now_str
        current_version = 1

    # 序列化 state 并清除 file_id（上传文件仅临时存在）
    state_dict = req.state.model_dump(by_alias=True)
    for inp in state_dict.get("inputs", []):
        inp["fileId"] = ""
    state_dict["uploaded_files"] = {}

    # Add save timestamp to state dict for version metadata
    state_dict["_saved_at"] = now_str

    # 写入 YAML
    yaml_str = build_yaml(req.state)
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # 写入 state 快照
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state_dict, f, ensure_ascii=False, indent=2)

    # 更新索引
    output_type = ""
    if req.state.output:
        output_type = req.state.output.plugin

    input_metas = [
        ConfigInputMeta(name=inp.name, param_key=inp.param_key, plugin=inp.plugin)
        for inp in req.state.inputs
    ]

    meta = ConfigMeta(
        id=config_id,
        scene_name=req.state.scene.name or "未命名配置",
        description=req.state.scene.description or "",
        input_count=len(req.state.inputs),
        output_type=output_type,
        version=req.state.scene.version or "1.0",
        updated_at=now_str,
        current_version=current_version,
        created_at=created_at,
        inputs=input_metas,
    )

    index = _load_index()
    # 如果同一个 ID 已存在则更新，否则追加
    existing = next((i for i, e in enumerate(index) if e.get("id") == config_id), None)
    if existing is not None:
        index[existing] = meta.model_dump()
    else:
        index.append(meta.model_dump())
    _save_index(index)

    return SaveConfigResponse(id=config_id)


@router.delete("/{config_id}")
async def delete_config(config_id: str):
    _validate_config_id(config_id)
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="配置不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    index = [e for e in index if e.get("id") != config_id]
    _save_index(index)

    for ext in (".yaml", ".state.json"):
        p = os.path.join(CONFIGS_DIR, f"{config_id}{ext}")
        if os.path.exists(p):
            os.remove(p)

    # Clean up versions directory
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    if os.path.isdir(versions_dir):
        shutil.rmtree(versions_dir)

    return {"ok": True}


@router.get("/{config_id}")
async def load_config(config_id: str):
    _validate_config_id(config_id)
    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    if not os.path.exists(state_path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="配置不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    with open(state_path, "r", encoding="utf-8") as f:
        state_dict = json.load(f)
    _migrate_state_dict(state_dict)
    return state_dict


@router.get("/{config_id}/yaml")
async def download_config_yaml(config_id: str):
    _validate_config_id(config_id)
    yaml_path = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
    if not os.path.exists(yaml_path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="配置不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    return FileResponse(
        yaml_path,
        media_type="application/x-yaml",
        filename=f"{config_id}.yaml",
        headers={"Content-Disposition": f'attachment; filename="pipeline.yaml"'},
    )


@router.post("/{config_id}/execute")
async def execute_config(config_id: str, req: ExecuteConfigRequest):
    _validate_config_id(config_id)
    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    if not os.path.exists(state_path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="配置不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    with open(state_path, "r", encoding="utf-8") as f:
        state_dict = json.load(f)

    _migrate_state_dict(state_dict)

    # Get config_version from index
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    config_version = entry.get("current_version") if entry else None

    # 用请求中的 file_id 填充各 input
    for inp in state_dict.get("inputs", []):
        param_key = inp.get("param_key", "")
        if param_key in req.files:
            inp["file_id"] = req.files[param_key]

    state = WizardState(**state_dict)

    exec_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC).isoformat()

    inputs_summary = [
        {"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key}
        for inp in state.inputs
    ]
    processors_summary = [
        {"name": p.name, "plugin": p.plugin}
        for p in state.processors
    ]
    output_type = state.output.plugin if state.output else ""
    scene_name = state.scene.name or ""

    try:
        output_path = execute_pipeline(state)
    except (ValueError, SyntaxError, TimeoutError) as e:
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id=config_id,
            config_version=config_version,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=str(e),
        )
        raise HTTPException(status_code=422, detail=str(e))
    except CheckpointError as e:
        checks = [r.model_dump() for r in e.results]
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id=config_id,
            config_version=config_version,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message="数据检查点未通过",
            checks_summary=checks,
        )
        raise HTTPException(status_code=422, detail={"message": "数据检查点未通过", "checks": checks})
    except Exception as e:
        logger.exception("pipeline execution failed")
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id=config_id,
            config_version=config_version,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

    filename = os.path.basename(output_path)
    finished_at = datetime.now(UTC).isoformat()

    # Compute duration
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)

    # Move output to executions directory
    exec_output_dir = os.path.join(EXEC_DIR, exec_id)
    os.makedirs(exec_output_dir, exist_ok=True)
    exec_output_path = os.path.join(exec_output_dir, filename)
    shutil.move(output_path, exec_output_path)

    # Save execution record
    record = ExecutionRecord(
        id=exec_id,
        config_id=config_id,
        config_version=config_version,
        scene_name=scene_name,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        inputs_summary=inputs_summary,
        processors_summary=processors_summary,
        output_type=output_type,
        checks_summary=[],
        output_file_name=filename,
    )

    result_path = os.path.join(exec_output_dir, "result.json")
    with open(result_path, "w") as f:
        json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

    _update_exec_index(record)

    media_type = (
        "text/csv"
        if filename.endswith(".csv")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        exec_output_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# === Version management helpers ===

def _read_version_state(config_id: str, version: int) -> dict | None:
    """Read a specific version's state.json. Returns None if not found."""
    # Check versions directory first
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    state_path = os.path.join(versions_dir, f"v{version}.state.json")
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Check if this is the current version
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    if entry and entry.get("current_version") == version:
        current_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
        if os.path.exists(current_path):
            with open(current_path, "r", encoding="utf-8") as f:
                return json.load(f)

    return None


def _list_version_files(config_id: str) -> list[int]:
    """Return sorted list of version numbers available for a config."""
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    versions = []
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
    if entry:
        cv = entry.get("current_version", 0)
        if cv > 0 and cv not in versions:
            versions.append(cv)

    return sorted(versions)


def _diff_dicts(d1: dict, d2: dict, path: str = "") -> list[dict]:
    """Recursively diff two dicts. Returns list of changes."""
    changes = []
    all_keys = set(d1.keys()) | set(d2.keys())
    for key in sorted(all_keys):
        full_path = f"{path}.{key}" if path else key
        if key not in d1:
            changes.append({"type": "added", "path": full_path, "new": d2[key]})
        elif key not in d2:
            changes.append({"type": "removed", "path": full_path, "old": d1[key]})
        elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
            changes.extend(_diff_dicts(d1[key], d2[key], full_path))
        elif isinstance(d1[key], list) and isinstance(d2[key], list):
            if d1[key] != d2[key]:
                changes.append({"type": "changed", "path": full_path, "old": d1[key], "new": d2[key]})
        elif d1[key] != d2[key]:
            changes.append({"type": "changed", "path": full_path, "old": d1[key], "new": d2[key]})
    return changes


# === Version endpoints ===

@router.get("/{config_id}/versions")
async def list_versions(config_id: str) -> list[ConfigVersionMeta]:
    _validate_config_id(config_id)
    versions = _list_version_files(config_id)
    result = []
    for v in versions:
        state = _read_version_state(config_id, v)
        if state is None:
            continue
        scene = state.get("scene") or {}
        output = state.get("output") or {}
        result.append(ConfigVersionMeta(
            version=v,
            scene_version=scene.get("version", "1.0"),
            change_summary=state.get("change_summary", ""),
            created_at=state.get("_saved_at", ""),
            input_count=len(state.get("inputs", [])),
            processor_count=len(state.get("processors", [])),
            output_type=output.get("plugin", ""),
        ))
    return result


@router.get("/{config_id}/versions/{version}")
async def get_version(config_id: str, version: int):
    _validate_config_id(config_id)
    state = _read_version_state(config_id, version)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="版本不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    # Remove internal timestamp from response
    state.pop("_saved_at", None)
    state.pop("change_summary", None)
    _migrate_state_dict(state)
    return state


@router.post("/{config_id}/versions/{version}/rollback")
async def rollback_version(config_id: str, version: int):
    _validate_config_id(config_id)

    # 1. Read the target version's state
    target_state = _read_version_state(config_id, version)
    if target_state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="目标版本不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    yaml_path = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
    versions_dir = os.path.join(CONFIGS_DIR, config_id)

    if not os.path.exists(state_path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="配置不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    # 2. Get current version number from index
    index = _load_index()
    entry_idx = next((i for i, e in enumerate(index) if e.get("id") == config_id), None)
    if entry_idx is None:
        raise HTTPException(status_code=404, detail="配置索引不存在")
    old_version = index[entry_idx].get("current_version", 1)

    # 3. Move current state to next version slot (save current as a version before overwriting)
    os.makedirs(versions_dir, exist_ok=True)
    for suffix in ("state.json", "yaml"):
        current_path = os.path.join(CONFIGS_DIR, f"{config_id}.{suffix}")
        target_path = os.path.join(versions_dir, f"v{old_version}.{suffix}")
        if os.path.exists(current_path):
            shutil.move(current_path, target_path)

    # 4. Copy target version's state to current position
    now_str = datetime.now(UTC).isoformat()
    target_state["_saved_at"] = now_str
    target_state["change_summary"] = f"Rolled back from v{old_version} to v{version}"

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(target_state, f, ensure_ascii=False, indent=2)

    # Rebuild YAML from restored state
    _migrate_state_dict(target_state)
    # Remove internal fields before constructing WizardState
    target_state.pop("_saved_at", None)
    target_state.pop("change_summary", None)
    restored_wizard = WizardState(**target_state)
    yaml_str = build_yaml(restored_wizard)
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # 5. Increment version number and update index
    new_version = old_version + 1
    index[entry_idx]["current_version"] = new_version
    index[entry_idx]["version"] = target_state.get("scene", {}).get("version", "1.0")
    index[entry_idx]["updated_at"] = now_str
    index[entry_idx]["input_count"] = len(target_state.get("inputs", []))
    output_type = (target_state.get("output") or {}).get("plugin", "")
    if output_type:
        index[entry_idx]["output_type"] = output_type
    _save_index(index)

    return {"new_version": new_version, "rolled_back_from": old_version, "rolled_back_to": version}


@router.get("/{config_id}/diff")
async def diff_versions(config_id: str, v1: int, v2: int):
    _validate_config_id(config_id)

    state1 = _read_version_state(config_id, v1)
    state2 = _read_version_state(config_id, v2)

    if state1 is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"版本 v{v1} 不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    if state2 is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"版本 v{v2} 不存在", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    # Strip internal fields before diffing
    for s in (state1, state2):
        s.pop("_saved_at", None)
        s.pop("change_summary", None)

    changes = _diff_dicts(state1, state2)
    return {"v1": v1, "v2": v2, "changes": changes}
