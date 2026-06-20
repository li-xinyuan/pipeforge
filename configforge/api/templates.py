from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from configforge.middleware.jwt import is_jwt_enabled, decode_token
from configforge.models.template import Template, TemplateRequirement
from configforge.models.wizard import ErrorResponse
from configforge.services.template_store import TemplateStore
from configforge.utils.security import validate_id
from configforge.services.audit_logger import log_audit

router = APIRouter()


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
def list_templates(category: str | None = None, search: str | None = None):
    templates = TemplateStore.list_templates(category=category, search=search)
    return {"items": templates, "total": len(templates)}


@router.get("/{template_id}", summary="获取模板详情", description="根据模板 ID 获取完整的模板信息，包括名称、描述、分类、标签和配置状态。")
def get_template(template_id: str):
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
def create_template(req: CreateTemplateRequest):
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
def update_template(template_id: str, req: UpdateTemplateRequest):
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
def delete_template(template_id: str, request: Request):
    _validate_template_id(template_id)

    # Require admin when JWT is enabled
    if is_jwt_enabled():
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail=ErrorResponse(
                    error="Authentication required", code="AUTH_REQUIRED", recoverable=True
                ).model_dump(),
            )
        payload = decode_token(auth_header[7:])
        if not payload or payload.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail=ErrorResponse(
                    error="Only admin can delete templates", code="FORBIDDEN", recoverable=True
                ).model_dump(),
            )

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
def instantiate_template(template_id: str):
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
def check_compatibility(template_id: str):
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
