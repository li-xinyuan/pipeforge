"""Additional unit tests for EmailNotifier — covers init, message construction,
auth, network errors, advanced template rendering, and default body template."""

from unittest.mock import MagicMock, patch

import pytest

from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.email import (
    EmailNotifier,
    _default_body_template,
    _render_template,
)


def _success_context() -> NotifyContext:
    return NotifyContext(
        execution_id="exec-001",
        config_name="月度报表",
        status="success",
        summary="处理 100 行数据",
        output_files=["report.xlsx", "summary.csv"],
        started_at="2026-06-18T08:00:00",
        finished_at="2026-06-18T08:01:00",
    )


def _failed_context() -> NotifyContext:
    return NotifyContext(
        execution_id="exec-002",
        config_name="日终汇总",
        status="failed",
        summary="SQL 执行失败",
        error_message="Table 'users' not found",
        started_at="2026-06-18T09:00:00",
        finished_at="2026-06-18T09:00:05",
    )


# ─── TestEmailNotifierInit ───


class TestEmailNotifierInit:
    def test_default_port_and_tls(self):
        notifier = EmailNotifier(smtp_host="smtp.example.com")
        assert notifier.smtp_port == 587
        assert notifier.use_tls is True

    def test_custom_subject_template(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            subject_template="自定义: {config_name} {status}",
        )
        assert notifier.subject_template == "自定义: {config_name} {status}"

    def test_custom_body_template(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            body_template="<p>{config_name}</p>",
        )
        assert notifier.body_template == "<p>{config_name}</p>"

    def test_default_subject_template_when_empty(self):
        notifier = EmailNotifier(smtp_host="smtp.example.com", subject_template="")
        assert notifier.subject_template == "ConfigForge 执行通知: {status}"

    def test_default_body_template_when_empty(self):
        notifier = EmailNotifier(smtp_host="smtp.example.com", body_template="")
        assert notifier.body_template == _default_body_template()

    def test_default_recipients_is_empty_list(self):
        notifier = EmailNotifier(smtp_host="smtp.example.com")
        assert notifier.recipients == []


# ─── TestEmailNotifierMessageConstruction ───


class TestEmailNotifierMessageConstruction:
    @pytest.mark.asyncio
    async def test_mime_message_from_header(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="sender@example.com",
            smtp_password="pass",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            sendmail_args = mock_server.sendmail.call_args
            msg_str = sendmail_args[0][2]
            assert "From: sender@example.com" in msg_str

    @pytest.mark.asyncio
    async def test_mime_message_to_header_single_recipient(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="sender@example.com",
            smtp_password="pass",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            sendmail_args = mock_server.sendmail.call_args
            msg_str = sendmail_args[0][2]
            assert "To: admin@example.com" in msg_str

    @pytest.mark.asyncio
    async def test_mime_message_multiple_recipients_joined_with_comma(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="sender@example.com",
            smtp_password="pass",
            recipients=["a@example.com", "b@example.com", "c@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            sendmail_args = mock_server.sendmail.call_args
            msg_str = sendmail_args[0][2]
            assert "To: a@example.com, b@example.com, c@example.com" in msg_str

    @pytest.mark.asyncio
    async def test_mime_message_subject_header(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="sender@example.com",
            smtp_password="pass",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            sendmail_args = mock_server.sendmail.call_args
            msg_str = sendmail_args[0][2]
            assert "Subject:" in msg_str

    @pytest.mark.asyncio
    async def test_mime_message_html_body(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="sender@example.com",
            smtp_password="pass",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            sendmail_args = mock_server.sendmail.call_args
            msg_str = sendmail_args[0][2]
            assert "Content-Type: text/html" in msg_str


# ─── TestEmailNotifierAuth ───


class TestEmailNotifierAuth:
    @pytest.mark.asyncio
    async def test_login_called_when_user_and_password_provided(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_password="secret",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            mock_server.login.assert_called_once_with("user@example.com", "secret")

    @pytest.mark.asyncio
    async def test_login_not_called_when_no_credentials(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="",
            smtp_password="",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            mock_server.login.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_not_called_when_only_user_no_password(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="user@example.com",
            smtp_password="",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            await notifier.send(_success_context())

            mock_server.login.assert_not_called()


# ─── TestEmailNotifierNetworkError ───


class TestEmailNotifierNetworkError:
    @pytest.mark.asyncio
    async def test_non_smtp_exception_caught_as_failure(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_server.starttls.side_effect = ConnectionRefusedError("连接被拒绝")
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())

            assert result.success is False
            assert "邮件发送失败" in result.message
            assert "连接被拒绝" in result.message
            assert result.provider == "email"

    @pytest.mark.asyncio
    async def test_os_error_caught_as_failure(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.side_effect = OSError("网络不可达")
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())

            assert result.success is False
            assert "邮件发送失败" in result.message

    @pytest.mark.asyncio
    async def test_timeout_error_caught_as_failure(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_server.sendmail.side_effect = TimeoutError("连接超时")
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())

            assert result.success is False
            assert "邮件发送失败" in result.message
            assert "连接超时" in result.message


# ─── TestRenderTemplateAdvanced ───


class TestRenderTemplateAdvanced:
    def test_all_template_variables_substituted(self):
        ctx = _success_context()
        template = (
            "{config_name}|{status}|{status_text}|{summary}|"
            "{execution_id}|{error_message}|{started_at}|{finished_at}|{output_files}"
        )
        result = _render_template(template, ctx)

        assert "月度报表" in result
        assert "success" in result
        assert "成功" in result
        assert "处理 100 行数据" in result
        assert "exec-001" in result
        assert "2026-06-18T08:00:00" in result
        assert "2026-06-18T08:01:00" in result

    def test_output_files_joined_with_comma(self):
        ctx = _success_context()
        result = _render_template("{output_files}", ctx)
        assert result == "report.xlsx, summary.csv"

    def test_empty_output_files_shows_none(self):
        ctx = NotifyContext(
            execution_id="exec-003",
            config_name="测试配置",
            status="success",
            summary="无输出",
            output_files=[],
        )
        result = _render_template("{output_files}", ctx)
        assert result == "无"

    def test_error_message_defaults_to_empty_string(self):
        ctx = _success_context()
        assert ctx.error_message is None
        result = _render_template("[{error_message}]", ctx)
        assert result == "[]"

    def test_error_message_rendered_when_present(self):
        ctx = _failed_context()
        result = _render_template("{error_message}", ctx)
        assert result == "Table 'users' not found"

    def test_status_text_success_mapping(self):
        ctx = NotifyContext(
            execution_id="exec-010",
            config_name="测试",
            status="success",
            summary="ok",
        )
        result = _render_template("{status_text}", ctx)
        assert result == "成功"

    def test_status_text_failed_mapping(self):
        ctx = NotifyContext(
            execution_id="exec-011",
            config_name="测试",
            status="failed",
            summary="err",
        )
        result = _render_template("{status_text}", ctx)
        assert result == "失败"


# ─── TestDefaultBodyTemplate ───


class TestDefaultBodyTemplate:
    def test_contains_html_and_body_tags(self):
        tpl = _default_body_template()
        assert "<html>" in tpl
        assert "</html>" in tpl
        assert "<body>" in tpl
        assert "</body>" in tpl

    def test_contains_h2_heading(self):
        tpl = _default_body_template()
        assert "<h2>" in tpl
        assert "</h2>" in tpl

    def test_contains_table_structure(self):
        tpl = _default_body_template()
        assert "<table" in tpl
        assert "</table>" in tpl
        assert "<tr>" in tpl
        assert "</tr>" in tpl
        assert "<td" in tpl

    def test_contains_key_template_variables(self):
        tpl = _default_body_template()
        assert "{config_name}" in tpl
        assert "{status_text}" in tpl
        assert "{summary}" in tpl
        assert "{output_files}" in tpl
        assert "{started_at}" in tpl
        assert "{finished_at}" in tpl

    def test_heading_includes_status_text(self):
        tpl = _default_body_template()
        assert "执行{status_text}" in tpl
