from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from configforge.models.template import Template, TemplateRequirement
from configforge.models.wizard import ErrorResponse
from configforge.services.template_store import TemplateStore
from configforge.utils.security import validate_id

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


@router.get("")
def list_templates(category: str | None = None, search: str | None = None):
    templates = TemplateStore.list_templates(category=category, search=search)
    return {"items": templates, "total": len(templates)}


@router.get("/{template_id}")
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


@router.post("")
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


@router.put("/{template_id}")
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


@router.delete("/{template_id}")
def delete_template(template_id: str):
    _validate_template_id(template_id)
    deleted = TemplateStore.delete_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Template not found", code="NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    return {"ok": True}


@router.post("/{template_id}/instantiate")
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


@router.post("/{template_id}/check-compatibility")
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
