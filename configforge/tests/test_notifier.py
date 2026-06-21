"""Unit tests for configforge.services.notifier module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.email import EmailNotifier, _render_template
from configforge.services.notifier.formatters import (
    format_dingtalk,
    format_feishu,
    format_generic,
    format_wecom,
)
from configforge.services.notifier.webhook import WebhookNotifier


def _success_context() -> NotifyContext:
    return NotifyContext(
        execution_id="exec-001",
        config_name="月度报表",
        status="success",
        summary="处理 100 行数据",
        output_files=["report.xlsx"],
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


# ─── Formatters ───


class TestFormatDingtalk:
    def test_success_format(self):
        result = format_dingtalk(_success_context())
        assert result["msgtype"] == "markdown"
        assert "成功" in result["markdown"]["title"]
        assert "月度报表" in result["markdown"]["text"]
        assert "report.xlsx" in result["markdown"]["text"]

    def test_failed_format(self):
        result = format_dingtalk(_failed_context())
        assert "失败" in result["markdown"]["title"]
        assert "Table 'users' not found" in result["markdown"]["text"]


class TestFormatWecom:
    def test_success_format(self):
        result = format_wecom(_success_context())
        assert result["msgtype"] == "markdown"
        assert "月度报表" in result["markdown"]["content"]

    def test_failed_format(self):
        result = format_wecom(_failed_context())
        assert "失败" in result["markdown"]["content"]
        assert "Table 'users' not found" in result["markdown"]["content"]


class TestFormatFeishu:
    def test_success_format(self):
        result = format_feishu(_success_context())
        assert result["msg_type"] == "interactive"
        assert result["card"]["header"]["template"] == "green"
        assert "月度报表" in str(result["card"]["elements"])

    def test_failed_format(self):
        result = format_feishu(_failed_context())
        assert result["card"]["header"]["template"] == "red"
        assert "Table 'users' not found" in str(result["card"]["elements"])


class TestFormatGeneric:
    def test_success_format(self):
        result = format_generic(_success_context())
        assert result["execution_id"] == "exec-001"
        assert result["config_name"] == "月度报表"
        assert result["status"] == "success"
        assert result["output_files"] == ["report.xlsx"]
        assert "error_message" not in result

    def test_failed_format(self):
        result = format_generic(_failed_context())
        assert result["status"] == "failed"
        assert result["error_message"] == "Table 'users' not found"
        assert "output_files" not in result


# ─── WebhookNotifier ───


class TestWebhookNotifier:
    @pytest.mark.asyncio
    async def test_send_success(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="generic")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await notifier.send(_success_context())
            assert result.success is True
            assert result.provider == "generic"

    @pytest.mark.asyncio
    async def test_send_http_error(self):
        notifier = WebhookNotifier(url="https://example.com/hook")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await notifier.send(_success_context())
            assert result.success is False
            assert "500" in result.message

    @pytest.mark.asyncio
    async def test_send_timeout_retries(self):
        import httpx
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=1)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await notifier.send(_success_context())
            assert result.success is False
            assert "timed out" in result.message.lower()
            # Should have retried: 2 calls (initial + 1 retry)
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_network_error_no_retry(self):
        import httpx
        notifier = WebhookNotifier(url="https://example.com/hook", max_retries=0)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await notifier.send(_success_context())
            assert result.success is False
            assert "Network error" in result.message

    @pytest.mark.asyncio
    async def test_build_payload_uses_provider_formatter(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="dingtalk")
        payload = notifier._build_payload(_success_context())
        assert payload["msgtype"] == "markdown"

    @pytest.mark.asyncio
    async def test_custom_headers_sent(self):
        notifier = WebhookNotifier(
            url="https://example.com/hook",
            headers={"X-Custom": "test"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await notifier.send(_success_context())
            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
            assert headers.get("X-Custom") == "test"

    @pytest.mark.asyncio
    async def test_unknown_provider_falls_back_to_generic(self):
        notifier = WebhookNotifier(url="https://example.com/hook", provider="unknown")
        payload = notifier._build_payload(_success_context())
        # Should use format_generic which produces a flat dict
        assert "execution_id" in payload
        assert "config_name" in payload


# ─── EmailNotifier ───


class TestEmailNotifier:
    @pytest.mark.asyncio
    async def test_send_success(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_user="test@example.com",
            smtp_password="pass",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())
            assert result.success is True
            assert result.provider == "email"
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_no_recipients(self):
        notifier = EmailNotifier(smtp_host="smtp.example.com", recipients=[])
        result = await notifier.send(_success_context())
        assert result.success is False
        assert "收件人" in result.message

    @pytest.mark.asyncio
    async def test_send_smtp_error(self):
        import smtplib
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_server.starttls.side_effect = smtplib.SMTPException("auth failed")
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())
            assert result.success is False
            assert "SMTP" in result.message

    @pytest.mark.asyncio
    async def test_send_without_tls(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=25,
            use_tls=False,
            recipients=["admin@example.com"],
        )
        with patch("configforge.services.notifier.email.smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            result = await notifier.send(_success_context())
            assert result.success is True
            mock_server.starttls.assert_not_called()


class TestRenderTemplate:
    def test_renders_context_variables(self):
        ctx = _success_context()
        result = _render_template("{config_name} {status_text}", ctx)
        assert "月度报表" in result
        assert "成功" in result

    def test_renders_failed_status(self):
        ctx = _failed_context()
        result = _render_template("{status_text}: {error_message}", ctx)
        assert "失败" in result
        assert "Table 'users' not found" in result
