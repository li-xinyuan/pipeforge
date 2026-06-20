"""API endpoints for notification management."""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from configforge.models.notification import (
    NotificationConfig,
    NotificationConfigCreate,
    NotificationConfigUpdate,
    NotificationHistoryEntry,
)
from configforge.services.notifier.base import NotifyContext, NotifyResult
from configforge.services.notifier.smtp_settings import (
    SmtpSettings,
    SmtpSettingsUpdate,
    load_settings as load_smtp_settings,
    save_settings as save_smtp_settings,
    mask_password,
)
from configforge.services.notifier.webhook import WebhookNotifier
from configforge.utils.security import validate_id
from configforge.utils.paths import get_data_dir
from configforge.utils.migration import load_with_migration

router = APIRouter(prefix="/api/notifications", tags=["通知管理"])

# ─── Persistence helpers ───

_DATA_DIR = get_data_dir()
_NOTIFICATIONS_PATH = Path(_DATA_DIR) / "notifications.json"
_HISTORY_PATH = Path(_DATA_DIR) / "notification_history.json"


def _load_notifications() -> list[NotificationConfig]:
    _NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = load_with_migration(str(_NOTIFICATIONS_PATH), default=[])
    if isinstance(data, list):
        return [NotificationConfig(**item) for item in data]
    return [NotificationConfig(**item) for item in data.get("notifications", [])]


def _save_notifications(configs: list[NotificationConfig]) -> None:
    _NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _NOTIFICATIONS_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump([c.model_dump() for c in configs], f, ensure_ascii=False, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.replace(_NOTIFICATIONS_PATH)


def _load_history() -> list[NotificationHistoryEntry]:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = load_with_migration(str(_HISTORY_PATH), default=[])
    if isinstance(data, list):
        return [NotificationHistoryEntry(**item) for item in data]
    return [NotificationHistoryEntry(**item) for item in data.get("history", [])]


def _save_history(entries: list[NotificationHistoryEntry]) -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Keep only last 200 entries
    entries = entries[-200:]
    tmp = _HISTORY_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump([e.model_dump() for e in entries], f, ensure_ascii=False, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    tmp.replace(_HISTORY_PATH)


def add_history_entry(entry: NotificationHistoryEntry) -> None:
    """Add a notification history entry (called by dispatcher)."""
    history = _load_history()
    history.append(entry)
    _save_history(history)


# ─── CRUD endpoints ───


@router.get("/configs", summary="获取通知配置列表", description="获取所有通知推送配置的列表，包括 Webhook 和邮件类型。")
async def api_list_notification_configs():
    """List all notification configs."""
    configs = _load_notifications()
    return [c.model_dump() for c in configs]


@router.post("/configs", summary="创建通知配置", description="创建一个新的通知推送配置。支持 Webhook（需提供 URL）和邮件类型。可配置启用状态、触发条件和通知模板。")
async def api_create_notification_config(req: NotificationConfigCreate):
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
    return config.model_dump()


@router.get("/configs/{config_id}", summary="获取通知配置详情", description="根据配置 ID 获取单个通知推送配置的详细信息。")
async def api_get_notification_config(config_id: str):
    """Get a single notification config."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    for c in configs:
        if c.id == config_id:
            return c.model_dump()
    raise HTTPException(status_code=404, detail="推送配置不存在")


@router.put("/configs/{config_id}", summary="更新通知配置", description="更新指定的通知推送配置。支持部分更新，只需提供需要修改的字段。Webhook 类型必须保留 URL。")
async def api_update_notification_config(config_id: str, req: NotificationConfigUpdate):
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
            return updated.model_dump()
    raise HTTPException(status_code=404, detail="推送配置不存在")


@router.delete("/configs/{config_id}", summary="删除通知配置", description="删除指定的通知推送配置。操作不可撤销。")
async def api_delete_notification_config(config_id: str):
    """Delete a notification config."""
    validate_id(config_id, "config_id")
    configs = _load_notifications()
    new_configs = [c for c in configs if c.id != config_id]
    if len(new_configs) == len(configs):
        raise HTTPException(status_code=404, detail="推送配置不存在")
    _save_notifications(new_configs)
    return {"ok": True}


@router.post("/test/{config_id}", summary="测试通知推送", description="向指定通知配置发送测试消息，验证推送是否正常工作。仅对已启用的配置有效。")
async def api_test_notification(config_id: str):
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
    return {"ok": result.success, "message": result.message, "provider": result.provider}


@router.get("/history", summary="获取通知历史", description="获取通知推送的历史记录列表。默认返回最近 50 条，可通过 limit 参数调整。最多保留 200 条历史记录。")
async def api_notification_history(limit: int = 50):
    """Get notification history."""
    history = _load_history()
    return [e.model_dump() for e in history[-limit:]]


# ─── SMTP settings endpoints ───


@router.get("/smtp-settings", summary="获取 SMTP 设置", description="获取当前 SMTP 邮件服务器的配置信息。密码字段会被脱敏显示。")
async def api_get_smtp_settings():
    """Get current SMTP settings (password is masked)."""
    settings = load_smtp_settings()
    data = settings.model_dump()
    data["password"] = mask_password(settings.password)
    return data


@router.put("/smtp-settings", summary="更新 SMTP 设置", description="更新 SMTP 邮件服务器配置，包括主机、端口、用户名、密码、TLS 设置和发件人地址。支持部分更新。")
async def api_update_smtp_settings(body: SmtpSettingsUpdate):
    """Update SMTP settings (partial update supported)."""
    existing = load_smtp_settings()
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
    save_smtp_settings(full_settings)
    return {"ok": True}


@router.post("/smtp-test", summary="测试 SMTP 连接", description="测试 SMTP 邮件服务器连接是否正常。向配置的发件人地址发送一封测试邮件，验证 SMTP 配置是否正确。")
async def api_test_smtp():
    """Test SMTP connection by sending a test email to the configured sender."""
    settings = load_smtp_settings()
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
    if not result.success:
        raise HTTPException(status_code=500, detail=f"SMTP 测试失败: {result.message}")
    return {"ok": True, "message": result.message, "provider": result.provider}


# ─── Send helper ───


async def _send_notification(config: NotificationConfig, context: NotifyContext) -> NotifyResult:
    """Send a notification using the given config and context."""
    if config.type == "webhook":
        notifier = WebhookNotifier(
            url=config.webhook_url,
            provider=config.webhook_provider,
            headers=config.webhook_headers,
        )
        return await notifier.send(context)

    if config.type == "email":
        from configforge.services.notifier.email import EmailNotifier

        # Read from SMTP settings file first, fall back to environment variables
        smtp = load_smtp_settings()
        if smtp.host:
            smtp_host = smtp.host
            smtp_port = smtp.port
            smtp_user = smtp.user
            smtp_password = smtp.password
            use_tls = smtp.use_tls
        else:
            smtp_host = os.environ.get("CONFIGFORGE_SMTP_HOST", "")
            smtp_port = int(os.environ.get("CONFIGFORGE_SMTP_PORT", "587"))
            smtp_user = os.environ.get("CONFIGFORGE_SMTP_USER", "")
            smtp_password = os.environ.get("CONFIGFORGE_SMTP_PASSWORD", "")
            use_tls = os.environ.get("CONFIGFORGE_SMTP_TLS", "true").lower() != "false"

        if not smtp_host:
            return NotifyResult(success=False, message="SMTP 未配置", provider="email")

        notifier = EmailNotifier(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            use_tls=use_tls,
            recipients=config.email_to,
            subject_template=config.email_subject_template,
            body_template=config.email_body_template,
        )
        return await notifier.send(context)

    return NotifyResult(success=False, message="未知推送类型", provider="unknown")
