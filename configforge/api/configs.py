import fcntl
import json
import os
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from configforge.core.pipeline import execute_pipeline
from configforge.models.wizard import (
    ConfigMeta,
    ConfigInputMeta,
    SaveConfigRequest,
    SaveConfigResponse,
    ExecuteConfigRequest,
    WizardState,
    ErrorResponse,
)
from configforge.services.yaml_builder import build_yaml
from configforge.utils.security import validate_id

router = APIRouter()

def _validate_config_id(config_id: str) -> str:
    try:
        return validate_id(config_id, "config_id")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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

    # 序列化 state 并清除 file_id（上传文件仅临时存在）
    state_dict = req.state.model_dump()
    for inp in state_dict.get("inputs", []):
        inp["file_id"] = ""
    state_dict["uploaded_files"] = {}

    # 写入 YAML
    yaml_str = build_yaml(req.state)
    yaml_path = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # 写入 state 快照
    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
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
        updated_at=datetime.now(UTC).isoformat(),
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
        return json.load(f)


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

    # 用请求中的 file_id 填充各 input
    for inp in state_dict.get("inputs", []):
        param_key = inp.get("param_key", "")
        if param_key in req.files:
            inp["file_id"] = req.files[param_key]

    state = WizardState(**state_dict)

    try:
        output_path = execute_pipeline(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = os.path.basename(output_path)
    media_type = (
        "text/csv"
        if filename.endswith(".csv")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        output_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
