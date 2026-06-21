"""Unit tests for the notifier dispatcher module.

Focuses on additional scenarios not covered by test_notifier_integration.py.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configforge.models.notification import NotificationConfig
from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.dispatcher import (
    build_notify_context,
    dispatch_notifications,
    dispatch_notifications_async,
    should_trigger,
)

# ---------------------------------------------------------------------------
# TestBuildNotifyContext
# ---------------------------------------------------------------------------


class TestBuildNotifyContext:
    """Tests for build_notify_context mapping and default behaviour."""

    def test_maps_all_fields_from_execution_result(self):
        result = {
            "execution_id": "exec-999",
            "config_name": "季度报表",
            "status": "failed",
            "summary": "连接超时",
            "output_files": ["a.xlsx", "b.csv"],
            "started_at": "2026-01-01T00:00:00",
            "finished_at": "2026-01-01T00:05:00",
            "error_message": "Timeout after 300s",
        }
        ctx = build_notify_context(result)
        assert ctx.execution_id == "exec-999"
        assert ctx.config_name == "季度报表"
        assert ctx.status == "failed"
        assert ctx.summary == "连接超时"
        assert ctx.output_files == ["a.xlsx", "b.csv"]
        assert ctx.started_at == "2026-01-01T00:00:00"
        assert ctx.finished_at == "2026-01-01T00:05:00"
        assert ctx.error_message == "Timeout after 300s"

    def test_handles_missing_fields_with_defaults(self):
        ctx = build_notify_context({})
        assert ctx.execution_id == ""
        assert ctx.config_name == "未知配置"
        assert ctx.status == "unknown"
        assert ctx.summary == ""
        assert ctx.output_files == []
        assert ctx.started_at == ""
        assert ctx.finished_at == ""
        assert ctx.error_message is None

    def test_maps_output_files_list(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "",
            "output_files": ["report.xlsx", "chart.png", "data.csv"],
        }
        ctx = build_notify_context(result)
        assert ctx.output_files == ["report.xlsx", "chart.png", "data.csv"]

    def test_empty_output_files_when_key_missing(self):
        result = {
            "execution_id": "e1",
            "config_name": "测试",
            "status": "success",
            "summary": "",
        }
        ctx = build_notify_context(result)
        assert ctx.output_files == []


# ---------------------------------------------------------------------------
# TestShouldTrigger
# ---------------------------------------------------------------------------


class TestShouldTrigger:
    """Tests for should_trigger filtering logic."""

    def _make_config(self, **overrides):
        defaults = dict(
            id="n1",
            name="test",
            type="webhook",
            enabled=True,
            webhook_url="https://example.com",
            trigger_on_success=True,
            trigger_on_failure=True,
            trigger_on_anomaly=False,
        )
        defaults.update(overrides)
        return NotificationConfig(**defaults)

    def _make_context(self, status="success"):
        return NotifyContext(
            execution_id="e1",
            config_name="test",
            status=status,
            summary="ok",
        )

    def test_disabled_config_returns_false(self):
        config = self._make_config(enabled=False)
        ctx = self._make_context(status="success")
        assert should_trigger(config, ctx) is False

    def test_trigger_on_success_matches_success(self):
        config = self._make_config(trigger_on_success=True, trigger_on_failure=False, trigger_on_anomaly=False)
        ctx = self._make_context(status="success")
        assert should_trigger(config, ctx) is True

    def test_trigger_on_failure_matches_failed(self):
        config = self._make_config(trigger_on_success=False, trigger_on_failure=True, trigger_on_anomaly=False)
        ctx = self._make_context(status="failed")
        assert should_trigger(config, ctx) is True

    def test_trigger_on_anomaly_matches_anomaly(self):
        config = self._make_config(trigger_on_success=False, trigger_on_failure=False, trigger_on_anomaly=True)
        ctx = self._make_context(status="anomaly")
        assert should_trigger(config, ctx) is True

    def test_all_triggers_disabled_returns_false_even_for_matching_status(self):
        config = self._make_config(trigger_on_success=False, trigger_on_failure=False, trigger_on_anomaly=False)
        for status in ("success", "failed", "anomaly"):
            ctx = self._make_context(status=status)
            assert should_trigger(config, ctx) is False

    def test_all_triggers_enabled_matches_any_status(self):
        config = self._make_config(trigger_on_success=True, trigger_on_failure=True, trigger_on_anomaly=True)
        for status in ("success", "failed", "anomaly"):
            ctx = self._make_context(status=status)
            assert should_trigger(config, ctx) is True

    def test_trigger_on_success_false_rejects_success(self):
        config = self._make_config(trigger_on_success=False, trigger_on_failure=True, trigger_on_anomaly=True)
        ctx = self._make_context(status="success")
        assert should_trigger(config, ctx) is False

    def test_trigger_on_failure_false_rejects_failed(self):
        config = self._make_config(trigger_on_success=True, trigger_on_failure=False, trigger_on_anomaly=True)
        ctx = self._make_context(status="failed")
        assert should_trigger(config, ctx) is False

    def test_trigger_on_anomaly_false_rejects_anomaly(self):
        config = self._make_config(trigger_on_success=True, trigger_on_failure=True, trigger_on_anomaly=False)
        ctx = self._make_context(status="anomaly")
        assert should_trigger(config, ctx) is False


# ---------------------------------------------------------------------------
# TestDispatchNotifications
# ---------------------------------------------------------------------------


class TestDispatchNotifications:
    """Tests for dispatch_notifications core dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatches_to_multiple_matching_configs(self):
        config_a = NotificationConfig(
            id="na", name="推送A", type="webhook",
            enabled=True, webhook_url="https://a.com",
        )
        config_b = NotificationConfig(
            id="nb", name="推送B", type="webhook",
            enabled=True, webhook_url="https://b.com",
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "OK"
        mock_result.provider = "generic"

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[config_a, config_b]),
            patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result) as mock_send,
            patch("configforge.services.notifier.dispatcher.add_history_entry") as mock_history,
        ):
            await dispatch_notifications({
                "execution_id": "exec-multi",
                "config_name": "多配置测试",
                "status": "success",
                "summary": "完成",
            })

        assert mock_send.call_count == 2
        assert mock_history.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        config = NotificationConfig(
            id="n1", name="推送", type="webhook",
            enabled=True, webhook_url="https://example.com",
        )

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[config]),
            patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, side_effect=Exception("network error")),
            patch("configforge.services.notifier.dispatcher.add_history_entry") as mock_history,
        ):
            # Should not raise
            await dispatch_notifications({
                "execution_id": "exec-err",
                "config_name": "异常测试",
                "status": "success",
                "summary": "完成",
            })

        # History should NOT be recorded for failed sends
        assert mock_history.call_count == 0

    @pytest.mark.asyncio
    async def test_records_history_for_each_successful_dispatch(self):
        config = NotificationConfig(
            id="n1", name="历史记录测试", type="webhook",
            enabled=True, webhook_url="https://example.com",
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Delivered"
        mock_result.provider = "dingtalk"

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[config]),
            patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result),
            patch("configforge.services.notifier.dispatcher.add_history_entry") as mock_history,
        ):
            await dispatch_notifications({
                "execution_id": "exec-hist",
                "config_name": "历史测试",
                "status": "success",
                "summary": "完成",
            })

        assert mock_history.call_count == 1
        entry = mock_history.call_args[0][0]
        assert entry.config_id == "n1"
        assert entry.config_name == "历史记录测试"
        assert entry.execution_id == "exec-hist"
        assert entry.pipeline_config_name == "历史测试"
        assert entry.status == "success"
        assert entry.notify_success is True
        assert entry.provider == "dingtalk"


# ---------------------------------------------------------------------------
# TestDispatchNotificationsAsync
# ---------------------------------------------------------------------------


class TestDispatchNotificationsAsync:
    """Tests for dispatch_notifications_async fire-and-forget wrapper."""

    def test_creates_task_when_loop_is_running(self):
        """When a running event loop exists, dispatch_notifications_async should
        create a task on it rather than blocking."""
        execution_result = {
            "execution_id": "exec-async",
            "config_name": "异步测试",
            "status": "success",
            "summary": "完成",
        }

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[]),
            patch("configforge.services.notifier.dispatcher.dispatch_notifications", new_callable=AsyncMock) as mock_dispatch,
        ):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Simulate a running loop by running inside it
                async def _run():
                    dispatch_notifications_async(execution_result)
                    # Give the task a chance to be created
                    await asyncio.sleep(0)

                loop.run_until_complete(_run())
            finally:
                loop.close()

        mock_dispatch.assert_awaited_once_with(execution_result)

    def test_handles_no_running_loop(self):
        """When no running event loop exists, dispatch_notifications_async
        should fall back to asyncio.run."""
        execution_result = {
            "execution_id": "exec-no-loop",
            "config_name": "无循环测试",
            "status": "failed",
            "summary": "出错",
        }

        with (
            patch("configforge.services.notifier.dispatcher._load_notifications", return_value=[]),
            patch("configforge.services.notifier.dispatcher.dispatch_notifications", new_callable=AsyncMock) as mock_dispatch,
        ):
            # No running loop, so it should call asyncio.run
            dispatch_notifications_async(execution_result)

        mock_dispatch.assert_awaited_once_with(execution_result)
