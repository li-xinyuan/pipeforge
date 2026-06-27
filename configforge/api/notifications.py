"""API endpoints for notification management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from configforge.middleware.auth import require_role
from configforge.models.notification import (
    NotificationConfig,
    NotificationConfigCreate,
    NotificationConfigUpdate,
    NotificationHistoryEntry,
)
from configforge.models.user import User
from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.sender import send_notification as _send_notification
from configforge.services.notifier.smtp_settings import (
    SmtpSettings,
    SmtpSettingsUpdate,
    mask_password,
)
from configforge.services.notifier.store import (
    load_history as _load_history,
)
from configforge.services.notifier.store import (
    load_notifications as _load_notifications,
)
from configforge.services.notifier.store import (
    save_notifications as _save_notifications,
)
from configforge.storage import get_audit_store, get_settings_store
from configforge.utils.security import validate_id

router = APIRouter(prefix="/api/notifications", tags=["通知管理"])

_audit = get_audit_store()
_smtp_store = get_settings_store('smtp')


class OkResponse(BaseModel):
    ok: bool


class NotifyTestResponse(BaseModel):
    ok: bool
    message: str = ""
    provider: str = ""


# ─── CRUD endpoints ───


@router.get("/configs", summary="获取通知配置列表", description="获取所有通知推送配置的列表，包括 Webhook 和邮件类型。", response_model=list[NotificationConfig])
async def api_list_notification_configs(_user: User = Depends(require_role("viewer", "editor", "admin"))):
    """List all notification configs."""
    configs = _load_notifications()
    return [c.model_dump() for c in configs]


@router.post("/configs", summary="创建通知配置", description="创建一个新的通知推送配置。支持 Webhook（需提供 URL）和邮件类型。可配置启用状态、触发条件和通知模板。", response_model=NotificationConfig)
async def api_create_notification_config(req: NotificationConfigCreate, _user: User = Depends(require_role("editor", "admin"))):
    """Create a new notification config."""
    if req.type == "webhook" and not req.webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL 不能为空")

    config = NotificationConfig(
        id=str(uuid.uuid4())[:8],
        **req.model_dump(),
    )
    configs = _load_notifications()
    configs.append(config)
    _save_notifications(configs)
    _audit.log_audit(
        action="create",
        target_type="notification_config",
        target_id=config.id,
        details={
            "user": _user.username,
            "name": config.name,
            "type": config.type,
            "enabled": config.enabled,
        },
    )
    return config.model_dump()


@router.get("/configs/{config_id}", summary="获取通知配置详情", description="根据配置 ID 获取单个通知推送配置的详细信息。", response_model=NotificationConfig)
async def api_get_notification_config(config_id: str, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    """Get a single notification config."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    for c in configs:
        if c.id == config_id:
            return c.model_dump()
    raise HTTPException(status_code=404, detail="推送配置不存在")


@router.put("/configs/{config_id}", summary="更新通知配置", description="更新指定的通知推送配置。支持部分更新，只需提供需要修改的字段。Webhook 类型必须保留 URL。", response_model=NotificationConfig)
async def api_update_notification_config(config_id: str, req: NotificationConfigUpdate, _user: User = Depends(require_role("editor", "admin"))):
    """Update a notification config."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    for i, c in enumerate(configs):
        if c.id == config_id:
            update_data = req.model_dump(exclude_none=True)
            updated = c.model_copy(update=update_data)
            if updated.type == "webhook" and not updated.webhook_url:
                raise HTTPException(status_code=400, detail="Webhook URL 不能为空")
            configs[i] = updated
            _save_notifications(configs)
            _audit.log_audit(
                action="update",
                target_type="notification_config",
                target_id=config_id,
                details={
                    "user": _user.username,
                    "name": updated.name,
                    "fields": list(update_data.keys()),
                },
            )
            return updated.model_dump()
    raise HTTPException(status_code=404, detail="推送配置不存在")


@router.delete("/configs/{config_id}", summary="删除通知配置", description="删除指定的通知推送配置。操作不可撤销。", response_model=OkResponse)
async def api_delete_notification_config(config_id: str, _user: User = Depends(require_role("editor", "admin"))):
    """Delete a notification config."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    new_configs = [c for c in configs if c.id != config_id]
    if len(new_configs) == len(configs):
        raise HTTPException(status_code=404, detail="推送配置不存在")
    _save_notifications(new_configs)
    _audit.log_audit(
        action="delete",
        target_type="notification_config",
        target_id=config_id,
        details={"user": _user.username},
    )
    return {"ok": True}


@router.post("/test/{config_id}", summary="测试通知推送", description="向指定通知配置发送测试消息，验证推送是否正常工作。仅对已启用的配置有效。", response_model=NotifyTestResponse)
async def api_test_notification(config_id: str, _user: User = Depends(require_role("editor", "admin"))):
    """Test a notification config by sending a test message."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    config = next((c for c in configs if c.id == config_id), None)
    if config is None:
        raise HTTPException(status_code=404, detail="推送配置不存在")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="推送配置已禁用")

    context = NotifyContext(
        execution_id="test-execution",
        config_name="测试配置",
        status="success",
        summary="这是一条测试推送消息",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
    )

    result = await _send_notification(config, context)
    _audit.log_audit(
        action="test",
        target_type="notification_config",
        target_id=config_id,
        details={
            "user": _user.username,
            "name": config.name,
            "type": config.type,
            "success": result.success,
        },
    )
    return {"ok": result.success, "message": result.message, "provider": result.provider}


@router.get("/history", summary="获取通知历史", description="获取通知推送的历史记录列表。默认返回最近 50 条，可通过 limit 参数调整。最多保留 200 条历史记录。", response_model=list[NotificationHistoryEntry])
async def api_notification_history(limit: int = 50, _user: User = Depends(require_role("viewer", "editor", "admin"))):
    """Get notification history."""
    history = _load_history()
    return [e.model_dump() for e in history[-limit:]]


# ─── SMTP settings endpoints ───


@router.get("/smtp-settings", summary="获取 SMTP 设置", description="获取当前 SMTP 邮件服务器的配置信息。密码字段会被脱敏显示。", response_model=dict)
async def api_get_smtp_settings(_user: User = Depends(require_role("admin"))):
    """Get current SMTP settings (password is masked)."""
    settings = _smtp_store.load_settings()
    data = settings.model_dump()
    data["password"] = mask_password(settings.password)
    return data


@router.put("/smtp-settings", summary="更新 SMTP 设置", description="更新 SMTP 邮件服务器配置，包括主机、端口、用户名、密码、TLS 设置和发件人地址。支持部分更新。", response_model=OkResponse)
async def api_update_smtp_settings(body: SmtpSettingsUpdate, _user: User = Depends(require_role("admin"))):
    """Update SMTP settings (partial update supported)."""
    existing = _smtp_store.load_settings()
    password = existing.password if body.password is None else body.password
    update_data = body.model_dump(exclude={"password"})
    # Only override fields that were explicitly provided
    for key, value in update_data.items():
        if value is not None:
            setattr(existing, key, value)
    full_settings = SmtpSettings(
        host=existing.host,
        port=existing.port,
        user=existing.user,
        password=password,
        use_tls=existing.use_tls,
        sender=existing.sender,
    )
    _smtp_store.save_settings(full_settings)
    _audit.log_audit(
        action="update",
        target_type="smtp_settings",
        target_id="default",
        details={
            "user": _user.username,
            "host": full_settings.host,
            "port": full_settings.port,
            "use_tls": full_settings.use_tls,
            "sender": full_settings.sender,
        },
    )
    return {"ok": True}


@router.post("/smtp-test", summary="测试 SMTP 连接", description="测试 SMTP 邮件服务器连接是否正常。向配置的发件人地址发送一封测试邮件，验证 SMTP 配置是否正确。", response_model=NotifyTestResponse)
async def api_test_smtp(_user: User = Depends(require_role("admin"))):
    """Test SMTP connection by sending a test email to the configured sender."""
    settings = _smtp_store.load_settings()
    if not settings.host:
        raise HTTPException(status_code=400, detail="SMTP 未配置，请先设置 SMTP 服务器地址")

    sender = settings.sender or settings.user
    if not sender:
        raise HTTPException(status_code=400, detail="未配置发件人地址")

    from configforge.services.notifier.email import EmailNotifier

    notifier = EmailNotifier(
        smtp_host=settings.host,
        smtp_port=settings.port,
        smtp_user=settings.user,
        smtp_password=settings.password,
        use_tls=settings.use_tls,
        recipients=[sender],
        subject_template="ConfigForge SMTP 测试",
        body_template="这是一封测试邮件，用于验证 SMTP 配置是否正确。",
    )
    context = NotifyContext(
        execution_id="smtp-test",
        config_name="SMTP 测试",
        status="success",
        summary="SMTP 连接测试",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    result = await notifier.send(context)
    _audit.log_audit(
        action="test",
        target_type="smtp_settings",
        target_id="default",
        details={
            "user": _user.username,
            "host": settings.host,
            "success": result.success,
        },
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=f"SMTP 测试失败: {result.message}")
    return {"ok": True, "message": result.message, "provider": result.provider}


# ─── Send helper ───


# _send_notification 已移至 services/notifier/sender.py，此处通过顶部 import re-export
