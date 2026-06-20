import json
import os
import shutil
import urllib.parse
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
    _sanitize_summary,
)
from configforge.services.yaml_builder import build_yaml
from configforge.services.execution_service import (
    execute as execute_service,
    ExecutionContext,
    ExecutionResult,
)
from configforge.utils.cache import TTLCache
from configforge.utils.security import validate_id, sanitize_connection_string
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.migration import load_with_migration, ensure_schema_version
from configforge.utils.paths import get_configs_dir
from configforge.services.audit_logger import log_audit

router = APIRouter()
logger = logging.getLogger(__name__)

def _validate_config_id(config_id: str) -> str:
    try:
        return validate_id(config_id, "config_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config_id format")


CONFIGS_DIR = get_configs_dir()
os.makedirs(CONFIGS_DIR, exist_ok=True)

INDEX_PATH = os.path.join(CONFIGS_DIR, "index.json")
_cache = TTLCache(ttl=5.0)


def _load_index() -> list[dict]:
    cached = _cache.get("index")
    if cached is not None:
        return cached
    data = load_with_migration(INDEX_PATH, default=[])
    if isinstance(data, list):
        result = data
    else:
        result = data.get("configs", [])
    _cache.set("index", result)
    return result


def _save_index(data: list[dict]) -> None:
    write_json_locked(INDEX_PATH, data)
    _cache.invalidate("index")


@router.get("", summary="获取配置列表", description="分页获取所有已保存的 Pipeline 配置列表。支持按场景名称和描述进行搜索。返回按更新时间倒序排列的配置元数据。")
async def list_configs(
    search: str = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    index = _load_index()
    # Sort by updated_at descending (newest first)
    index = sorted(index, key=lambda e: e.get("updated_at", ""), reverse=True)
    if search:
        q = search.lower()
        index = [e for e in index
                 if q in e.get("scene_name", "").lower()
                 or q in e.get("description", "").lower()]
    total = len(index)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    items = [ConfigMeta(**e) for e in index[start:start + page_size]]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("", response_model=SaveConfigResponse, summary="保存配置", description="创建或更新一个 Pipeline 配置。如果是更新已有配置，旧版本会自动归档到版本历史中。同时生成对应的 YAML 配置文件。")
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
    write_json_locked(state_path, state_dict)

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


@router.delete("/{config_id}", summary="删除配置", description="删除指定的 Pipeline 配置，包括其状态文件、YAML 文件和所有版本历史。操作不可撤销。")
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

    log_audit("delete", "config", config_id)

    return {"ok": True}


@router.get("/{config_id}", summary="获取配置详情", description="根据配置 ID 获取完整的 Pipeline 状态数据，包括场景信息、输入源、处理器和输出配置。")
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
    state_dict = read_json_locked(state_path)
    state_dict = ensure_schema_version(state_dict, state_path)
    return state_dict


@router.get("/{config_id}/yaml", summary="下载配置 YAML", description="下载指定配置的 Pipeline YAML 文件。YAML 文件包含完整的 Pipeline 定义，可用于版本控制和迁移。")
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


@router.post("/{config_id}/execute", summary="执行已保存的配置", description="执行指定 ID 的已保存 Pipeline 配置。可通过 files 参数为各输入源指定上传文件。支持文件输出和数据库输出。")
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

    state_dict = read_json_locked(state_path)

    state_dict = ensure_schema_version(state_dict, state_path)
    # Remove internal fields that are not part of WizardState schema
    state_dict.pop("_saved_at", None)
    state_dict.pop("change_summary", None)
    state_dict.pop("schema_version", None)

    # Get config_version from index
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    config_version = entry.get("current_version") if entry else None

    # 用请求中的 file_id 填充各 input
    for inp in state_dict.get("inputs", []):
        param_key = inp.get("param_key", "") or inp.get("paramKey", "")
        if param_key in req.files:
            inp["file_id"] = req.files[param_key]

    state = WizardState(**state_dict)

    context = ExecutionContext(
        config_id=config_id,
        config_version=config_version,
    )

    result = await execute_service(state, context, sanitize_errors=True)

    log_audit("execute", "config", config_id)

    if result.status == "failed":
        if result.checks:
            raise HTTPException(status_code=422, detail={"message": "数据检查点未通过", "checks": result.checks})
        raise HTTPException(status_code=422, detail=result.error_message)

    # Return file download for file-based outputs, or JSON for database outputs
    if result.output_file_name and result.output_path:
        media_type = (
            "text/csv"
            if result.output_file_name.endswith(".csv")
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        encoded_name = urllib.parse.quote(result.output_file_name)
        return FileResponse(
            result.output_path,
            media_type=media_type,
            filename=result.output_file_name,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
        )
    else:
        return {"ok": True, "status": "success", "output_type": context.output_type}


# === Version management helpers ===

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


def _diff_states(state1: dict, state2: dict) -> dict:
    """Diff two config state dicts using deepdiff. Returns structured changes."""
    from deepdiff import DeepDiff

    diff = DeepDiff(state1, state2, ignore_order=True, verbose_level=2)
    changes = []

    for change_type, items in diff.items():
        if change_type == "values_changed":
            for path, detail in items.items():
                changes.append({
                    "type": "changed",
                    "path": path,
                    "old": detail.get("old_value"),
                    "new": detail.get("new_value"),
                })
        elif change_type == "dictionary_item_added":
            for path in items:
                changes.append({
                    "type": "added",
                    "path": str(path) if not isinstance(path, str) else path,
                    "new": items[path] if isinstance(items, dict) else None,
                })
        elif change_type == "dictionary_item_removed":
            for path in items:
                changes.append({
                    "type": "removed",
                    "path": str(path) if not isinstance(path, str) else path,
                    "old": items[path] if isinstance(items, dict) else None,
                })
        elif change_type == "iterable_item_added":
            for path, detail in items.items():
                changes.append({
                    "type": "added",
                    "path": str(path),
                    "new": detail,
                })
        elif change_type == "iterable_item_removed":
            for path, detail in items.items():
                changes.append({
                    "type": "removed",
                    "path": str(path),
                    "old": detail,
                })
        elif change_type == "type_changes":
            for path, detail in items.items():
                changes.append({
                    "type": "changed",
                    "path": path,
                    "old": str(detail.get("old_type")),
                    "new": str(detail.get("new_type")),
                })

    return {"v1": None, "v2": None, "changes": changes}


# === Version endpoints ===

@router.get("/{config_id}/versions", summary="获取配置版本列表", description="获取指定配置的所有历史版本列表。每个版本包含版本号、场景版本、变更摘要、创建时间等信息。")
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


@router.get("/{config_id}/versions/{version}", summary="获取指定版本详情", description="获取指定配置的特定版本状态数据。可用于查看历史配置或进行版本对比。")
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
    state = ensure_schema_version(state, f"version:{config_id}:v{version}")
    state.pop("schema_version", None)
    return state


@router.post("/{config_id}/versions/{version}/rollback", summary="回滚到指定版本", description="将配置回滚到指定的历史版本。当前版本会自动归档，回滚后的内容将作为新版本保存。")
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

    write_json_locked(state_path, target_state)

    # Rebuild YAML from restored state
    target_state = ensure_schema_version(target_state, state_path)
    # Remove internal fields before constructing WizardState
    target_state.pop("_saved_at", None)
    target_state.pop("change_summary", None)
    target_state.pop("schema_version", None)
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


@router.get("/{config_id}/diff", summary="对比两个版本差异", description="对比指定配置的两个版本之间的差异。使用 deepdiff 进行深度对比，返回新增、修改、删除等变更详情。")
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

    result = _diff_states(state1, state2)
    result["v1"] = v1
    result["v2"] = v2
    return result
