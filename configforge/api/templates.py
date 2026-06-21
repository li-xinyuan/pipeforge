import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from configforge.middleware.auth import require_role
from configforge.models.user import User
from configforge.models.wizard import ErrorResponse
from configforge.services.audit_logger import log_audit
from configforge.services.template_store import TemplateStore
from configforge.utils.security import validate_id

router = APIRouter(tags=["模板管理"])


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = "general"
    tags: list[str] = []
    config_state: dict
    author: str = ""


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    author: str | None = None
    version: str | None = None
    config_state: dict | None = None


def _validate_template_id(template_id: str) -> str:
    try:
        return validate_id(template_id, "template_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template_id format")


@router.get("", summary="获取模板列表", description="获取所有可用的 Pipeline 模板列表。支持按分类筛选和按名称搜索。返回模板的基本信息和配置状态。")
def list_templates(category: str | None = None, search: str | None = None, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    templates = TemplateStore.list_templates(category=category, search=search)
    return {"items": templates, "total": len(templates)}


@router.get("/{template_id}", summary="获取模板详情", description="根据模板 ID 获取完整的模板信息，包括名称、描述、分类、标签和配置状态。")
def get_template(template_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_template_id(template_id)
    template = TemplateStore.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    return template


@router.post("", summary="创建模板", description="创建一个新的 Pipeline 模板。模板包含名称、描述、分类、标签和配置状态，可被其他用户复用。")
def create_template(req: CreateTemplateRequest, _user: User = Depends(require_role("admin"))):
    template = TemplateStore.create_template(
        name=req.name,
        description=req.description,
        category=req.category,
        tags=req.tags,
        config_state=req.config_state,
        author=req.author,
    )
    return template


@router.put("/{template_id}", summary="更新模板", description="更新指定模板的信息。支持部分更新，只需提供需要修改的字段（名称、描述、分类、标签、作者、版本、配置状态）。")
def update_template(template_id: str, req: UpdateTemplateRequest, _user: User = Depends(require_role("admin"))):
    _validate_template_id(template_id)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="No fields to update", code="VALIDATION_ERROR", recoverable=True
            ).model_dump(),
        )
    template = TemplateStore.update_template(template_id, **updates)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    return template


@router.delete("/{template_id}", summary="删除模板", description="删除指定的 Pipeline 模板。仅管理员可执行此操作。操作不可撤销。")
def delete_template(template_id: str, _user: User = Depends(require_role("admin"))):
    _validate_template_id(template_id)

    deleted = TemplateStore.delete_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    log_audit("delete", "template", template_id)
    return {"ok": True}


@router.post("/{template_id}/instantiate", summary="实例化模板", description="从指定模板创建一个新的 Pipeline 配置实例。返回模板的配置状态数据，可直接用于创建新配置。同时会增加模板的使用计数。")
def instantiate_template(template_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_template_id(template_id)
    template = TemplateStore.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    TemplateStore.increment_usage(template_id)
    return {"config_state": template["config_state"], "template_id": template_id}


@router.post("/{template_id}/check-compatibility", summary="检查模板兼容性", description="检查指定模板的前置依赖是否满足。验证数据库连接、AI 服务配置等需求是否已就绪，返回每个依赖项的状态和建议。")
def check_compatibility(template_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    _validate_template_id(template_id)
    template = TemplateStore.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )

    issues = []
    requirements = template.get("requirements", [])

    for req in requirements:
        req_type = req.get("type", "")
        req_desc = req.get("description", "")

        if req_type == "database":
            from configforge.services.connection_store import ConnectionStore
            connections = ConnectionStore.list_all()
            if connections:
                issues.append({
                    "requirement": req_desc,
                    "status": "met",
                    "suggestion": f"Found {len(connections)} configured database connection(s)",
                })
            else:
                issues.append({
                    "requirement": req_desc,
                    "status": "missing",
                    "suggestion": "Please configure a database connection in Settings before using this template",
                })

        elif req_type == "ai":
            from configforge.services.ai.settings import load_settings
            ai_settings = load_settings()
            if ai_settings.enabled and ai_settings.api_key:
                issues.append({
                    "requirement": req_desc,
                    "status": "met",
                    "suggestion": "AI service is configured and ready",
                })
            else:
                issues.append({
                    "requirement": req_desc,
                    "status": "missing",
                    "suggestion": "Please configure AI service (API key) in Settings before using this template",
                })

        elif req_type == "input_format":
            issues.append({
                "requirement": req_desc,
                "status": "met",
                "suggestion": "All input formats are supported",
            })

    compatible = all(issue["status"] == "met" for issue in issues)
    return {"compatible": compatible, "issues": issues}


@router.get("/{template_id}/export", summary="导出模板", description="将指定模板导出为 JSON 文件，可用于备份或分享。")
async def export_template(template_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    """导出模板为 JSON 文件"""
    _validate_template_id(template_id)
    template = TemplateStore.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail={"error": "模板不存在", "code": "NOT_FOUND"},
        )
    return JSONResponse(content=template, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''template_{template_id}.json"
    })


@router.post("/import", summary="导入模板", description="从 JSON 文件导入模板。会自动生成新 ID 避免与现有模板冲突。")
async def import_template(file: UploadFile = File(...), _user: User = Depends(require_role("editor", "admin"))):
    """导入模板 JSON 文件"""
    content = await file.read()
    try:
        template_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"error": "无效的 JSON 文件", "code": "INVALID_JSON"},
        )

    # 验证模板格式
    required_fields = {"name", "category", "config_state"}
    if not isinstance(template_data, dict) or not required_fields.issubset(template_data.keys()):
        raise HTTPException(
            status_code=400,
            detail={"error": "模板格式不正确，缺少必要字段 (name, category, config_state)", "code": "VALIDATION_ERROR"},
        )

    # create_template 会自动生成新 ID，避免冲突
    template = TemplateStore.create_template(
        name=template_data["name"],
        description=template_data.get("description", ""),
        category=template_data["category"],
        tags=template_data.get("tags", []),
        config_state=template_data["config_state"],
        author=template_data.get("author", ""),
    )

    log_audit("import", "template", template["id"])
    return {"message": "模板导入成功", "id": template["id"]}
