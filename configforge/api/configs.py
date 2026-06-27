"""Pipeline 配置管理路由 (P1-4c 重构)。

重构说明：
- 业务逻辑已移至 services/config_service.py (ConfigService)
- 存储原语由 ConfigService 注入的 ConfigStoreProtocol 承担
- 本模块仅保留 HTTP 装配层：请求解析、响应构造、错误转换

向后兼容（测试 patch 点）：
保留对 config_store 模块常量与函数的 re-export，使测试可继续
monkeypatch configs_mod.CONFIGS_DIR / INDEX_PATH / _cache。
"""

import io
import urllib.parse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from configforge.middleware.auth import require_role
from configforge.models.user import User
from configforge.models.wizard import (
    ErrorResponse,
    ExecuteConfigRequest,
    SaveConfigRequest,
    SaveConfigResponse,
)
from configforge.services.config_service import ConfigService
from configforge.utils.security import validate_id

router = APIRouter(tags=["配置管理"])


# 模块级单例（与原行为一致；测试可通过 patch config_store 常量影响其内部存储）
_service = ConfigService()


def _validate_config_id(config_id: str) -> str:
    try:
        return validate_id(config_id, "config_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid config_id format")


def _not_found(msg: str = "配置不存在") -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorResponse(error=msg, code="NOT_FOUND", recoverable=True).model_dump(),
    )


# ============================================================================
# Re-export for backward compat (tests monkeypatch configs_mod.INDEX_PATH etc.)
# 业务逻辑已迁出，这些常量仅供测试 patch 注入隔离数据目录。
# ============================================================================
from configforge.services.config_store import (  # noqa: F401  re-export for tests
    CONFIGS_DIR,
    INDEX_PATH,
    INDEX_SCHEMA_VERSION,
    _cache,
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
    return _service.list_configs(
        search=search, page=page, page_size=page_size, sort=sort, order=order,
    )


@router.post("", response_model=SaveConfigResponse, summary="保存配置", description="创建或更新一个 Pipeline 配置。如果是更新已有配置，旧版本会自动归档到版本历史中。同时生成对应的 YAML 配置文件。")
async def save_config(req: SaveConfigRequest, _user: User = Depends(require_role("editor", "admin"))):
    return _service.save_config(req, _user)


@router.delete("/{config_id}", summary="删除配置", description="删除指定的 Pipeline 配置，包括其状态文件、YAML 文件和所有版本历史。操作不可撤销。")
async def delete_config(config_id: str, _user: User = Depends(require_role("editor", "admin"))):
    _validate_config_id(config_id)
    try:
        _service.delete_config(config_id)
    except KeyError:
        raise _not_found()
    return {"ok": True}


@router.get("/{config_id}", summary="获取配置详情", description="根据配置 ID 获取完整的 Pipeline 状态数据，包括场景信息、输入源、处理器和输出配置。")
async def load_config(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_config_id(config_id)
    try:
        return _service.load_config(config_id)
    except KeyError:
        raise _not_found()


@router.get("/{config_id}/yaml", summary="下载配置 YAML", description="下载指定配置的 Pipeline YAML 文件。YAML 文件包含完整的 Pipeline 定义，可用于版本控制和迁移。")
async def download_config_yaml(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_config_id(config_id)
    import os

    yaml_path = _service.get_yaml_path(config_id)
    if not os.path.exists(yaml_path):
        raise _not_found()
    return FileResponse(
        yaml_path,
        media_type="application/x-yaml",
        filename=f"{config_id}.yaml",
        headers={"Content-Disposition": 'attachment; filename="pipeline.yaml"'},
    )


@router.get("/{config_id}/export", summary="导出配置", description="导出指定配置的完整状态为 YAML 或 JSON 文件，可用于备份或迁移到其他实例。")
async def export_config(
    config_id: str,
    format: str = "yaml",
    _user: User = Depends(require_role("viewer", "editor", "admin")),
):
    _validate_config_id(config_id)
    try:
        result = _service.export_config(config_id, fmt=format)
    except KeyError:
        raise _not_found()
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=str(e), code="INVALID_FORMAT", recoverable=True,
            ).model_dump(),
        )

    return StreamingResponse(
        io.BytesIO(result["content"]),
        media_type=result["media_type"],
        headers={"Content-Disposition": result["disposition"]},
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
                error="未提供文件", code="NO_FILE", recoverable=True,
            ).model_dump(),
        )

    raw_bytes = await file.read()
    try:
        result = _service.import_config(file.filename, raw_bytes, _user)
    except ValueError as e:
        # 区分校验错误码
        msg = str(e)
        if "过大" in msg:
            code = "FILE_TOO_LARGE"
        elif "编码" in msg:
            code = "ENCODING_ERROR"
        elif "解析失败" in msg:
            code = "PARSE_ERROR"
        elif "必须是对象" in msg:
            code = "INVALID_FORMAT"
        elif "校验失败" in msg:
            code = "VALIDATION_ERROR"
        else:
            code = "INVALID_FORMAT"
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error=msg, code=code, recoverable=True).model_dump(),
        )

    return result


@router.post("/{config_id}/execute", summary="执行已保存的配置", description="执行指定 ID 的已保存 Pipeline 配置。可通过 files 参数为各输入源指定上传文件。支持文件输出和数据库输出。")
async def execute_config(config_id: str, req: ExecuteConfigRequest, _user: User = Depends(require_role("editor", "admin"))):
    _validate_config_id(config_id)
    try:
        result, context = await _service.execute_config(config_id, req)
    except KeyError:
        raise _not_found()

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


# === Version endpoints ===

@router.get("/{config_id}/versions", summary="获取配置版本列表", description="获取指定配置的所有历史版本列表。每个版本包含版本号、场景版本、变更摘要、创建时间等信息。", response_model=list)
async def list_versions(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_config_id(config_id)
    return _service.list_versions(config_id)


@router.get("/{config_id}/versions/diff", summary="对比两个版本差异", description="对比指定配置的两个版本之间的差异。使用 deepdiff 进行深度对比，返回新增、修改、删除等变更详情。")
async def diff_versions(config_id: str, v1: int, v2: int, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_config_id(config_id)
    try:
        return _service.diff_versions(config_id, v1, v2)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"版本 {e} 不存在", code="NOT_FOUND", recoverable=True,
            ).model_dump(),
        )


@router.get("/{config_id}/versions/{version}", summary="获取指定版本详情", description="获取指定配置的特定版本状态数据。可用于查看历史配置或进行版本对比。")
async def get_version(config_id: str, version: int, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_config_id(config_id)
    try:
        return _service.get_version(config_id, version)
    except KeyError:
        raise _not_found("版本不存在")


@router.post("/{config_id}/versions/{version}/rollback", summary="回滚到指定版本", description="将配置回滚到指定的历史版本。当前版本会自动归档，回滚后的内容将作为新版本保存。")
async def rollback_version(config_id: str, version: int, _user: User = Depends(require_role("editor", "admin"))):
    _validate_config_id(config_id)
    try:
        return _service.rollback_version(config_id, version, _user)
    except KeyError as e:
        raise _not_found(str(e) if str(e) else "目标版本不存在")
