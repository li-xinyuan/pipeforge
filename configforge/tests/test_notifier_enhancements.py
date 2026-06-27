"""Unit tests for T-5D-04: Pipeline execution notification enhancements.

Tests cover:
1. Enhanced NotifyContext fields (duration_seconds, row_count, error_type)
2. Template rendering with {{variable}} placeholders
3. Frequency control (cooldown period)
4. build_notify_context extracting enhanced fields from execution_result
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configforge.models.notification import NotificationConfig
from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.dispatcher import (
    _is_within_cooldown,
    _record_trigger,
    build_notify_context,
    dispatch_notifications,
    reset_frequency_control,
)
from configforge.services.notifier.formatters import (
    format_dingtalk,
    format_generic,
    get_template_variables,
    render_template,
)
from configforge.services.notifier.webhook import WebhookNotifier


# ---------------------------------------------------------------------------
# TestBuildNotifyContextEnhanced
# ---------------------------------------------------------------------------


class TestBuildNotifyContextEnhanced:
    """Tests for enhanced build_notify_context with duration, row_count, etc."""

    def test_extracts_duration_from_duration_ms(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "ok",
            "duration_ms": 1500,
        }
        ctx = build_notify_context(result)
        assert ctx.duration_seconds == 1.5

    def test_extracts_duration_from_started_finished_at(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "ok",
            "started_at": "2026-06-18T08:00:00+00:00",
            "finished_at": "2026-06-18T08:00:30+00:00",
        }
        ctx = build_notify_context(result)
        assert ctx.duration_seconds is not None
        assert abs(ctx.duration_seconds - 30.0) < 0.1

    def test_extracts_duration_seconds_directly(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "ok",
            "duration_seconds": 42.5,
        }
        ctx = build_notify_context(result)
        assert ctx.duration_seconds == 42.5

    def test_extracts_row_count(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "ok",
            "row_count": 1234,
        }
        ctx = build_notify_context(result)
        assert ctx.row_count == 1234

    def test_extracts_error_type(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "failed",
            "summary": "error",
            "error_type": "ConnectionError",
        }
        ctx = build_notify_context(result)
        assert ctx.error_type == "ConnectionError"

    def test_extracts_stack_summary(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "failed",
            "summary": "error",
            "stack_summary": "Traceback ...",
        }
        ctx = build_notify_context(result)
        assert ctx.stack_summary == "Traceback ..."

    def test_duration_none_when_no_time_info(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "ok",
        }
        ctx = build_notify_context(result)
        assert ctx.duration_seconds is None

    def test_preserves_backward_compatibility(self):
        """Existing execution_result format should still work."""
        result = {
            "execution_id": "exec-999",
            "config_name": "季度报表",
            "status": "failed",
            "summary": "连接超时",
            "output_files": ["a.xlsx"],
            "started_at": "2026-01-01T00:00:00",
            "finished_at": "2026-01-01T00:05:00",
            "error_message": "Timeout",
        }
        ctx = build_notify_context(result)
        assert ctx.execution_id == "exec-999"
        assert ctx.config_name == "季度报表"
        assert ctx.status == "failed"
        assert ctx.error_message == "Timeout"
        assert ctx.output_files == ["a.xlsx"]


# ---------------------------------------------------------------------------
# TestTemplateRendering
# ---------------------------------------------------------------------------


class TestTemplateRendering:
    """Tests for render_template with variable substitution."""

    def _make_context(self) -> NotifyContext:
        return NotifyContext(
            execution_id="exec-123",
            config_name="月度报表",
            status="success",
            summary="处理完成",
            output_files=["report.xlsx"],
            started_at="2026-06-18T08:00:00",
            finished_at="2026-06-18T08:01:00",
            error_message=None,
            duration_seconds=60.0,
            row_count=1000,
        )

    def test_renders_config_name(self):
        ctx = self._make_context()
        result = render_template("配置: {{config_name}}", ctx)
        assert result == "配置: 月度报表"

    def test_renders_status(self):
        ctx = self._make_context()
        result = render_template("状态: {{status}}", ctx)
        assert result == "状态: success"

    def test_renders_duration(self):
        ctx = self._make_context()
        result = render_template("耗时: {{duration}}", ctx)
        assert "1m" in result

    def test_renders_rows(self):
        ctx = self._make_context()
        result = render_template("行数: {{rows}}", ctx)
        assert "1,000" in result

    def test_renders_error_when_present(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="failed",
            summary="",
            error_message="Connection refused",
        )
        result = render_template("错误: {{error}}", ctx)
        assert result == "错误: Connection refused"

    def test_renders_error_empty_when_none(self):
        ctx = self._make_context()
        result = render_template("错误: {{error}}", ctx)
        assert result == "错误: "

    def test_renders_output_files(self):
        ctx = self._make_context()
        result = render_template("文件: {{output_files}}", ctx)
        assert "report.xlsx" in result

    def test_renders_multiple_variables(self):
        ctx = self._make_context()
        template = "[{{status}}] {{config_name}} - {{duration}} - {{rows}}行"
        result = render_template(template, ctx)
        assert "[success]" in result
        assert "月度报表" in result
        assert "1,000行" in result

    def test_unknown_variable_left_as_is(self):
        ctx = self._make_context()
        result = render_template("Hello {{unknown_var}}", ctx)
        assert "{{unknown_var}}" in result

    def test_handles_whitespace_in_variable(self):
        ctx = self._make_context()
        result = render_template("{{  config_name  }}", ctx)
        assert result == "月度报表"

    def test_no_variables_returns_unchanged(self):
        ctx = self._make_context()
        template = "Hello world, no variables here"
        result = render_template(template, ctx)
        assert result == template

    def test_get_template_variables_returns_list(self):
        variables = get_template_variables()
        assert isinstance(variables, list)
        assert "config_name" in variables
        assert "status" in variables
        assert "duration" in variables
        assert "rows" in variables
        assert "error" in variables


# ---------------------------------------------------------------------------
# TestEnhancedFormatters
# ---------------------------------------------------------------------------


class TestEnhancedFormatters:
    """Tests that formatters include enhanced fields (duration, rows)."""

    def test_dingtalk_includes_duration_when_present(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="success",
            summary="ok",
            duration_seconds=30.0,
        )
        payload = format_dingtalk(ctx)
        text = payload["markdown"]["text"]
        assert "耗时" in text

    def test_dingtalk_includes_rows_when_present(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="success",
            summary="ok",
            row_count=500,
        )
        payload = format_dingtalk(ctx)
        text = payload["markdown"]["text"]
        assert "行数" in text
        assert "500" in text

    def test_dingtalk_omits_duration_when_none(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="success",
            summary="ok",
        )
        payload = format_dingtalk(ctx)
        text = payload["markdown"]["text"]
        assert "耗时" not in text

    def test_generic_includes_duration(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="success",
            summary="ok",
            duration_seconds=5.5,
            row_count=100,
        )
        payload = format_generic(ctx)
        assert payload["duration_seconds"] == 5.5
        assert payload["row_count"] == 100

    def test_generic_omits_optional_fields_when_none(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="test",
            status="success",
            summary="ok",
        )
        payload = format_generic(ctx)
        assert "duration_seconds" not in payload
        assert "row_count" not in payload
        assert "error_message" not in payload


# ---------------------------------------------------------------------------
# TestFrequencyControl
# ---------------------------------------------------------------------------


class TestFrequencyControl:
    """Tests for notification frequency control (cooldown period)."""

    def setup_method(self):
        reset_frequency_control()

    def teardown_method(self):
        reset_frequency_control()

    def test_first_notification_not_in_cooldown(self):
        assert _is_within_cooldown("cfg1", "pipe1", "success") is False

    def test_second_notification_within_cooldown(self):
        _record_trigger("cfg1", "pipe1", "success")
        assert _is_within_cooldown("cfg1", "pipe1", "success") is True

    def test_different_status_not_in_cooldown(self):
        _record_trigger("cfg1", "pipe1", "success")
        assert _is_within_cooldown("cfg1", "pipe1", "failed") is False

    def test_different_pipeline_not_in_cooldown(self):
        _record_trigger("cfg1", "pipe1", "success")
        assert _is_within_cooldown("cfg1", "pipe2", "success") is False

    def test_different_config_not_in_cooldown(self):
        _record_trigger("cfg1", "pipe1", "success")
        assert _is_within_cooldown("cfg2", "pipe1", "success") is False

    def test_custom_cooldown_zero_allows_immediate(self):
        _record_trigger("cfg1", "pipe1", "success")
        assert _is_within_cooldown("cfg1", "pipe1", "success", cooldown_seconds=0) is False

    @pytest.mark.asyncio
    async def test_dispatch_skips_within_cooldown(self):
        """Dispatch should skip notifications within cooldown period."""
        config = NotificationConfig(
            id="n1", name="test", type="webhook",
            enabled=True, webhook_url="https://example.com",
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "OK"
        mock_result.provider = "generic"

        execution_result = {
            "execution_id": "e1",
            "config_id": "pipe1",
            "config_name": "测试",
            "status": "success",
            "summary": "完成",
        }

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[config]),
            patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result) as mock_send,
            patch("configforge.services.notifier.dispatcher.add_history_entry"),
        ):
            # First dispatch — should send
            await dispatch_notifications(execution_result)
            assert mock_send.call_count == 1

            # Second dispatch — should be skipped due to cooldown
            await dispatch_notifications(execution_result)
            assert mock_send.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_dispatch_sends_after_cooldown_expires(self):
        """Dispatch should send after cooldown period expires."""
        config = NotificationConfig(
            id="n1", name="test", type="webhook",
            enabled=True, webhook_url="https://example.com",
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "OK"
        mock_result.provider = "generic"

        execution_result = {
            "execution_id": "e1",
            "config_id": "pipe1",
            "config_name": "测试",
            "status": "success",
            "summary": "完成",
        }

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[config]),
            patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result) as mock_send,
            patch("configforge.services.notifier.dispatcher.add_history_entry"),
            patch("configforge.services.notifier.dispatcher._is_within_cooldown", return_value=False),
        ):
            # Both should send since _is_within_cooldown is mocked to always return False
            await dispatch_notifications(execution_result)
            await dispatch_notifications(execution_result)
            assert mock_send.call_count == 2


# ---------------------------------------------------------------------------
# TestMessageTemplateInWebhookNotifier
# ---------------------------------------------------------------------------


class TestMessageTemplateInWebhookNotifier:
    """Tests that WebhookNotifier respects message_template."""

    def test_template_overrides_dingtalk_text(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="测试配置",
            status="success",
            summary="完成",
            duration_seconds=30.0,
            row_count=100,
        )
        notifier = WebhookNotifier(
            url="https://example.com",
            provider="dingtalk",
            message_template="自定义: {{config_name}} 状态={{status}} 耗时={{duration}}",
        )
        payload = notifier._build_payload(ctx)
        assert "自定义: 测试配置" in payload["markdown"]["text"]
        assert "状态=success" in payload["markdown"]["text"]

    def test_template_overrides_generic_message(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="测试",
            status="success",
            summary="ok",
        )
        notifier = WebhookNotifier(
            url="https://example.com",
            provider="generic",
            message_template="Custom: {{config_name}} - {{status}}",
        )
        payload = notifier._build_payload(ctx)
        assert payload["message"] == "Custom: 测试 - success"

    def test_no_template_uses_default_formatter(self):
        ctx = NotifyContext(
            execution_id="e1",
            config_name="测试",
            status="success",
            summary="ok",
        )
        notifier = WebhookNotifier(
            url="https://example.com",
            provider="generic",
        )
        payload = notifier._build_payload(ctx)
        # Default formatter should not have "message" key
        assert "message" not in payload
        assert payload["config_name"] == "测试"
