"""通知发送逻辑。

从 api/notifications.py 抽取，解除 service→api 反向依赖。
"""
import os

from configforge.models.notification import NotificationConfig
from configforge.services.notifier.base import NotifyContext, NotifyResult
from configforge.services.notifier.webhook import WebhookNotifier
from configforge.storage import get_settings_store

_smtp_store = get_settings_store("smtp")


async def send_notification(
    config: NotificationConfig, context: NotifyContext
) -> NotifyResult:
    """Send a notification using the given config and context."""
    if config.type == "webhook":
        notifier = WebhookNotifier(
            url=config.webhook_url,
            provider=config.webhook_provider,
            headers=config.webhook_headers,
            message_template=config.message_template,
        )
        return await notifier.send(context)

    if config.type == "email":
        from configforge.services.notifier.email import EmailNotifier

        # Read from SMTP settings file first, fall back to environment variables
        smtp = _smtp_store.load_settings()
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
