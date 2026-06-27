import io
import json
import logging
import os
import shutil
import urllib.parse
import uuid
from datetime import UTC, datetime

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from configforge.middleware.auth import require_role
from configforge.models.user import User
from configforge.models.wizard import (
    ConfigInputMeta,
    ConfigMeta,
    ConfigVersionMeta,
    ErrorResponse,
    ExecuteConfigRequest,
    SaveConfigRequest,
    SaveConfigResponse,
    WizardState,
)
from configforge.services.execution_service import (
    ExecutionContext,
)
from configforge.services.execution_service import (
    execute as execute_service,
)
from configforge.services.yaml_builder import build_yaml
from configforge.storage import get_audit_store
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.migration import ensure_schema_version
from configforge.utils.security import validate_id

router = APIRouter(tags=["配置管理"])
logger = logging.getLogger(__name__)

_audit = get_audit_store()

def _validate_config_id(config_id: str) -> str:
    try:
        return validate_id(config_id, "config_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config_id format")


# Storage layer extracted to services/config_store.py (T-5E-01)
# Re-exported for backward compat (tests monkeypatch configs_mod.INDEX_PATH etc.)
from configforge.services.config_store import (  # noqa: F401
    CONFIGS_DIR,
    INDEX_PATH,
    INDEX_SCHEMA_VERSION,
    _cache,
    _load_index,
    _save_index,
)


@router.get("", summary="获取配置列表", description="分页获取所有已保存的 Pipeline 配置列表。支持按场景名称和描述进行搜索，支持排序。仅返回索引字段，不读取 state.json。")
async def list_configs(
    search: str = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "updated_at",
    order: str = "desc",
    _user: User = Depends(require_role("viewer", "editor", "admin")),
) -> dict:
    index = _load_index()

    # Search filter
    if search:
        q = search.lower()
        index = [e for e in index
                 if q in e.get("scene_name", "").lower()
                 or q in e.get("description", "").lower()
                 or q in e.get("name", "").lower()
                 or any(q in t for t in e.get("tags", []))]

    # Sort
    reverse = order.lower() == "desc"
    # Map "name" to "scene_name" for backward compatibility
    sort_key = "scene_name" if sort == "name" else sort
    index = sorted(index, key=lambda e: e.get(sort_key, ""), reverse=reverse)

    total = len(index)
    start = (page - 1) * page_size
    items = [ConfigMeta(**e) for e in index[start:start + page_size]]
    return {
        "configs": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=SaveConfigResponse, summary="保存配置", description="创建或更新一个 Pipeline 配置。如果是更新已有配置，旧版本会自动归档到版本历史中。同时生成对应的 YAML 配置文件。")
async def save_config(req: SaveConfigRequest, _user: User = Depends(require_role("editor", "admin"))):
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

    # Extract input_types from inputs
    input_types = list(dict.fromkeys(inp.plugin for inp in req.state.inputs))

    # Extract tags from scene
    tags = req.state.scene.tags

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
        tags=tags,
        input_types=input_types,
    )

    index = _load_index()
    # 如果同一个 ID 已存在则更新，否则追加
    existing = next((i for i, e in enumerate(index) if e.get("id") == config_id), None)
    if existing is not None:
        index[existing] = meta.model_dump()
    else:
        index.append(meta.model_dump())
    _save_index(index)

    _audit.log_audit(
        action="update" if is_update else "create",
        target_type="config",
        target_id=config_id,
        details={
            "user": _user.username,
            "scene_name": meta.scene_name,
            "version": current_version,
        },
    )

    return SaveConfigResponse(id=config_id)


@router.delete("/{config_id}", summary="删除配置", description="删除指定的 Pipeline 配置，包括其状态文件、YAML 文件和所有版本历史。操作不可撤销。")
async def delete_config(config_id: str, _user: User = Depends(require_role("editor", "admin"))):
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

    _audit.log_audit("delete", "config", config_id)

    return {"ok": True}


@router.get("/{config_id}", summary="获取配置详情", description="根据配置 ID 获取完整的 Pipeline 状态数据，包括场景信息、输入源、处理器和输出配置。")
async def load_config(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
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
async def download_config_yaml(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
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
        headers={"Content-Disposition": 'attachment; filename="pipeline.yaml"'},
    )


def _serialize_state_for_export(state_dict: dict) -> dict:
    """Strip internal fields before exporting state."""
    out = {k: v for k, v in state_dict.items() if k not in ("_saved_at", "change_summary", "schema_version")}
    return out


@router.get("/{config_id}/export", summary="导出配置", description="导出指定配置的完整状态为 YAML 或 JSON 文件，可用于备份或迁移到其他实例。")
async def export_config(
    config_id: str,
    format: str = "yaml",
    _user: User = Depends(require_role("viewer", "editor", "admin")),
):
    _validate_config_id(config_id)
    if format not in ("yaml", "json"):
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="格式仅支持 yaml 或 json", code="INVALID_FORMAT", recoverable=True
            ).model_dump(),
        )
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
    export_data = _serialize_state_for_export(state_dict)
    # Include export metadata
    export_data["_export"] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "config_id": config_id,
        "format_version": 1,
    }

    # Get scene name for filename
    scene_name = (state_dict.get("scene") or {}).get("name", config_id)
    safe_name = "".join(c if c.isascii() and (c.isalnum() or c in "-_") else "_" for c in scene_name)[:40] or config_id

    if format == "json":
        content = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
        media_type = "application/json"
        filename = f"{safe_name}.json"
    else:
        content = yaml.safe_dump(export_data, allow_unicode=True, sort_keys=False).encode("utf-8")
        media_type = "application/x-yaml"
        filename = f"{safe_name}.yaml"

    # Build Content-Disposition header with RFC 5987 encoding for non-ASCII filenames
    from urllib.parse import quote
    disposition = f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{quote(filename)}'

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


@router.post("/import", summary="导入配置", description="导入 YAML/JSON 配置文件创建新配置。文件必须是 ConfigForge 导出的格式，包含完整的 WizardState。")
async def import_config(
    file: UploadFile = File(...),
    _user: User = Depends(require_role("editor", "admin")),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="未提供文件", code="NO_FILE", recoverable=True
            ).model_dump(),
        )

    # Read file content
    raw_bytes = await file.read()
    if len(raw_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="文件过大（限制 5MB）", code="FILE_TOO_LARGE", recoverable=True
            ).model_dump(),
        )

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="文件编码错误，请使用 UTF-8", code="ENCODING_ERROR", recoverable=True
            ).model_dump(),
        )

    # Determine format by extension or content
    filename_lower = (file.filename or "").lower()
    if filename_lower.endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=f"JSON 解析失败：{e}", code="PARSE_ERROR", recoverable=True
                ).model_dump(),
            )
    else:
        # Default to YAML (also handles .yaml/.yml)
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            # Try JSON as fallback
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error=f"YAML/JSON 解析失败：{e}", code="PARSE_ERROR", recoverable=True
                    ).model_dump(),
                )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="配置内容必须是对象", code="INVALID_FORMAT", recoverable=True
            ).model_dump(),
        )

    # Strip export metadata
    data.pop("_export", None)
    # Strip internal fields that may be present
    for k in ("_saved_at", "change_summary", "schema_version"):
        data.pop(k, None)

    # Validate as WizardState
    try:
        state = WizardState(**data)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error=f"配置格式校验失败：{e}", code="VALIDATION_ERROR", recoverable=True
            ).model_dump(),
        )

    # Save as a new config (always new ID to avoid overwriting)
    new_config_id = uuid.uuid4().hex
    now_str = datetime.now(UTC).isoformat()
    state_path = os.path.join(CONFIGS_DIR, f"{new_config_id}.state.json")
    yaml_path = os.path.join(CONFIGS_DIR, f"{new_config_id}.yaml")

    state_dict = state.model_dump(by_alias=True)
    # Clear file_id (uploaded files don't transfer)
    for inp in state_dict.get("inputs", []):
        inp["fileId"] = ""
    state_dict["uploaded_files"] = {}
    state_dict["_saved_at"] = now_str
    state_dict["change_summary"] = "Imported from external file"

    # Write YAML
    yaml_str = build_yaml(state)
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # Write state
    write_json_locked(state_path, state_dict)

    # Update index
    output_type = state.output.plugin if state.output else ""
    input_metas = [
        ConfigInputMeta(name=inp.name, param_key=inp.param_key, plugin=inp.plugin)
        for inp in state.inputs
    ]
    input_types = list(dict.fromkeys(inp.plugin for inp in state.inputs))
    tags = state.scene.tags

    meta = ConfigMeta(
        id=new_config_id,
        scene_name=state.scene.name or "导入的配置",
        description=state.scene.description or "",
        input_count=len(state.inputs),
        output_type=output_type,
        version=state.scene.version or "1.0",
        updated_at=now_str,
        current_version=1,
        created_at=now_str,
        inputs=input_metas,
        tags=tags,
        input_types=input_types,
    )

    index = _load_index()
    index.append(meta.model_dump())
    _save_index(index)

    _audit.log_audit(
        action="import",
        target_type="config",
        target_id=new_config_id,
        details={
            "user": _user.username,
            "scene_name": meta.scene_name,
            "source_filename": file.filename,
        },
    )

    return {"id": new_config_id, "scene_name": meta.scene_name}


@router.post("/{config_id}/execute", summary="执行已保存的配置", description="执行指定 ID 的已保存 Pipeline 配置。可通过 files 参数为各输入源指定上传文件。支持文件输出和数据库输出。")
async def execute_config(config_id: str, req: ExecuteConfigRequest, _user: User = Depends(require_role("editor", "admin"))):
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
            # state.json 以 by_alias=True 保存，字段名为 fileId（camelCase）。
            # InputSource 设有 extra="forbid"，若同时存在 fileId 和 file_id 会触发
            # extra_forbidden 错误，因此统一使用 alias fileId 写入。
            inp["fileId"] = req.files[param_key]
            inp.pop("file_id", None)

    state = WizardState(**state_dict)

    context = ExecutionContext(
        config_id=config_id,
        config_version=config_version,
    )

    result = await execute_service(state, context, sanitize_errors=True)

    _audit.log_audit("execute", "config", config_id)

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


# Version management helpers extracted to services/config_store.py (T-5E-01)
from configforge.services.config_store import _list_version_files, _read_version_state


def _deep_diff(old: any, new: any, path: str, result: dict) -> None:
    """Recursively compare two values and collect structured diff into result."""
    if old == new:
        return

    # Both are dicts — recurse by key
    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old.keys()) | set(new.keys())
        for key in sorted(all_keys):
            child_path = f"{path}.{key}" if path else key
            if key not in old:
                result["added"].append({"path": child_path, "value": new[key]})
            elif key not in new:
                result["removed"].append({"path": child_path, "value": old[key]})
            else:
                _deep_diff(old[key], new[key], child_path, result)
        return

    # Both are lists — compare by index
    if isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(old):
                result["added"].append({"path": child_path, "value": new[i]})
            elif i >= len(new):
                result["removed"].append({"path": child_path, "value": old[i]})
            else:
                _deep_diff(old[i], new[i], child_path, result)
        return

    # Scalar or type mismatch — treat as modified
    result["modified"].append({"path": path, "old": old, "new": new})


def _diff_states(state1: dict, state2: dict) -> dict:
    """Diff two config state dicts. Returns structured changes with dot-notation paths."""
    result: dict = {"added": [], "removed": [], "modified": []}
    _deep_diff(state1, state2, "", result)
    return result


# === Version endpoints ===

@router.get("/{config_id}/versions", summary="获取配置版本列表", description="获取指定配置的所有历史版本列表。每个版本包含版本号、场景版本、变更摘要、创建时间等信息。", response_model=list[ConfigVersionMeta])
async def list_versions(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))) -> list[ConfigVersionMeta]:
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


@router.get("/{config_id}/versions/diff", summary="对比两个版本差异", description="对比指定配置的两个版本之间的差异。使用 deepdiff 进行深度对比，返回新增、修改、删除等变更详情。")
async def diff_versions(config_id: str, v1: int, v2: int, _user: User = Depends(require_role("viewer", "editor", "admin"))):
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
    return {"v1": v1, "v2": v2, **result}


@router.get("/{config_id}/versions/{version}", summary="获取指定版本详情", description="获取指定配置的特定版本状态数据。可用于查看历史配置或进行版本对比。")
async def get_version(config_id: str, version: int, _user: User = Depends(require_role("viewer", "editor", "admin"))):
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
async def rollback_version(config_id: str, version: int, _user: User = Depends(require_role("editor", "admin"))):
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

    _audit.log_audit(
        action="rollback",
        target_type="config",
        target_id=config_id,
        details={
            "user": _user.username,
            "rolled_back_from": old_version,
            "rolled_back_to": version,
            "new_version": new_version,
        },
    )

    return {"new_version": new_version, "rolled_back_from": old_version, "rolled_back_to": version}
