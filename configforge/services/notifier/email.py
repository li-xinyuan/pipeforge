"""Email notifier using SMTP."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from .base import NotifierBase, NotifyContext, NotifyResult


class EmailNotifier(NotifierBase):
    """Sends notifications via SMTP email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        use_tls: bool = True,
        recipients: list[str] | None = None,
        subject_template: str = "",
        body_template: str = "",
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.recipients = recipients or []
        self.subject_template = subject_template or "ConfigForge 执行通知: {status}"
        self.body_template = body_template or _default_body_template()

    async def send(self, context: NotifyContext) -> NotifyResult:
        if not self.recipients:
            return NotifyResult(success=False, message="未配置收件人", provider="email")

        subject = _render_template(self.subject_template, context)
        body = _render_template(self.body_template, context)

        msg = MIMEMultipart()
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            server.sendmail(self.smtp_user, self.recipients, msg.as_string())
            server.quit()
            return NotifyResult(success=True, message="邮件已发送", provider="email")

        except smtplib.SMTPException as exc:
            return NotifyResult(success=False, message=f"SMTP 错误: {exc}", provider="email")
        except Exception as exc:
            return NotifyResult(success=False, message=f"邮件发送失败: {exc}", provider="email")


def _render_template(template: str, context: NotifyContext) -> str:
    """Simple template rendering with context variables."""
    status_text = "成功" if context.status == "success" else "失败"
    return template.format(
        config_name=context.config_name,
        status=context.status,
        status_text=status_text,
        summary=context.summary,
        execution_id=context.execution_id,
        error_message=context.error_message or "",
        started_at=context.started_at,
        finished_at=context.finished_at,
        output_files=", ".join(context.output_files) if context.output_files else "无",
    )


def _default_body_template() -> str:
    return """<html><body>
<h2>ConfigForge 执行{status_text}</h2>
<table style="border-collapse:collapse;min-width:400px;">
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">配置名称</td><td style="padding:6px 12px;border:1px solid #ddd;">{config_name}</td></tr>
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">执行状态</td><td style="padding:6px 12px;border:1px solid #ddd;">{status_text}</td></tr>
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">摘要</td><td style="padding:6px 12px;border:1px solid #ddd;">{summary}</td></tr>
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">输出文件</td><td style="padding:6px 12px;border:1px solid #ddd;">{output_files}</td></tr>
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">开始时间</td><td style="padding:6px 12px;border:1px solid #ddd;">{started_at}</td></tr>
<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:bold;">完成时间</td><td style="padding:6px 12px;border:1px solid #ddd;">{finished_at}</td></tr>
</table>
</body></html>"""
