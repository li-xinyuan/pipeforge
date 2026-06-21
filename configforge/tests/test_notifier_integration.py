"""Integration tests for notification dispatch after pipeline execution."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    """Use temp directory for notification data files."""
    monkeypatch.setattr(
        "configforge.api.notifications._NOTIFICATIONS_PATH",
        tmp_path / "notifications.json",
    )
    monkeypatch.setattr(
        "configforge.api.notifications._HISTORY_PATH",
        tmp_path / "notification_history.json",
    )


class TestDispatcherIntegration:
    @pytest.mark.asyncio
    async def test_dispatch_builds_context(self):
        """Test that build_notify_context correctly maps execution result."""
        from configforge.services.notifier.dispatcher import build_notify_context

        result = {
            "execution_id": "exec-123",
            "config_id": "cfg-456",
            "config_name": "月度报表",
            "status": "success",
            "summary": "处理 100 行",
            "output_files": ["report.xlsx"],
            "started_at": "2026-06-18T08:00:00",
            "finished_at": "2026-06-18T08:01:00",
        }
        ctx = build_notify_context(result)
        assert ctx.execution_id == "exec-123"
        assert ctx.config_name == "月度报表"
        assert ctx.status == "success"
        assert ctx.output_files == ["report.xlsx"]

    @pytest.mark.asyncio
    async def test_should_trigger_filters_disabled(self):
        """Test that disabled configs are skipped."""
        from configforge.models.notification import NotificationConfig
        from configforge.services.notifier.base import NotifyContext
        from configforge.services.notifier.dispatcher import should_trigger

        config = NotificationConfig(
            id="n1", name="test", type="webhook",
            enabled=False, webhook_url="https://example.com",
        )
        ctx = NotifyContext(
            execution_id="e1", config_name="test", status="success", summary="ok",
        )
        assert should_trigger(config, ctx) is False

    @pytest.mark.asyncio
    async def test_should_trigger_filters_by_status(self):
        """Test that trigger_on_success/failure filters work."""
        from configforge.models.notification import NotificationConfig
        from configforge.services.notifier.base import NotifyContext
        from configforge.services.notifier.dispatcher import should_trigger

        # Only trigger on failure
        config = NotificationConfig(
            id="n1", name="test", type="webhook",
            enabled=True, webhook_url="https://example.com",
            trigger_on_success=False, trigger_on_failure=True,
        )
        success_ctx = NotifyContext(
            execution_id="e1", config_name="test", status="success", summary="ok",
        )
        failed_ctx = NotifyContext(
            execution_id="e2", config_name="test", status="failed", summary="err",
        )
        assert should_trigger(config, success_ctx) is False
        assert should_trigger(config, failed_ctx) is True

    @pytest.mark.asyncio
    async def test_dispatch_sends_and_records_history(self, tmp_path):
        """Test that dispatch sends notification and records history."""
        from configforge.api.notifications import _save_notifications
        from configforge.models.notification import NotificationConfig
        from configforge.services.notifier.dispatcher import dispatch_notifications

        # Create a notification config
        config = NotificationConfig(
            id="n1", name="钉钉推送", type="webhook",
            enabled=True, webhook_url="https://example.com/hook",
            webhook_provider="dingtalk",
        )
        _save_notifications([config])

        # Mock the webhook send
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Delivered"
        mock_result.provider = "dingtalk"

        with patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result):
            await dispatch_notifications({
                "execution_id": "exec-001",
                "config_id": "cfg-001",
                "config_name": "月度报表",
                "status": "success",
                "summary": "处理完成",
                "started_at": "2026-06-18T08:00:00",
                "finished_at": "2026-06-18T08:01:00",
            })

        # Check history was recorded
        from configforge.api.notifications import _load_history
        history = _load_history()
        assert len(history) == 1
        assert history[0].config_name == "钉钉推送"
        assert history[0].notify_success is True
        assert history[0].pipeline_config_name == "月度报表"

    @pytest.mark.asyncio
    async def test_dispatch_skips_non_matching_config_ids(self, tmp_path):
        """Test that config_ids filter works."""
        from configforge.api.notifications import _load_history, _save_notifications
        from configforge.models.notification import NotificationConfig
        from configforge.services.notifier.dispatcher import dispatch_notifications

        # Config only triggers for cfg-A
        config = NotificationConfig(
            id="n1", name="特定配置推送", type="webhook",
            enabled=True, webhook_url="https://example.com/hook",
            config_ids=["cfg-A"],
        )
        _save_notifications([config])

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "OK"
        mock_result.provider = "generic"

        with patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, return_value=mock_result):
            # Should NOT trigger for cfg-B
            await dispatch_notifications({
                "execution_id": "exec-002",
                "config_id": "cfg-B",
                "config_name": "其他配置",
                "status": "success",
                "summary": "完成",
            })
            history = _load_history()
            assert len(history) == 0

            # Should trigger for cfg-A
            await dispatch_notifications({
                "execution_id": "exec-003",
                "config_id": "cfg-A",
                "config_name": "目标配置",
                "status": "success",
                "summary": "完成",
            })
            history = _load_history()
            assert len(history) == 1

    @pytest.mark.asyncio
    async def test_dispatch_does_not_raise_on_failure(self, tmp_path):
        """Test that notification failures don't affect the caller."""
        from configforge.api.notifications import _save_notifications
        from configforge.models.notification import NotificationConfig
        from configforge.services.notifier.dispatcher import dispatch_notifications

        config = NotificationConfig(
            id="n1", name="推送", type="webhook",
            enabled=True, webhook_url="https://example.com/hook",
        )
        _save_notifications([config])

        # Mock a failing send
        with patch("configforge.services.notifier.dispatcher._send_notification", new_callable=AsyncMock, side_effect=Exception("boom")):
            # Should not raise
            await dispatch_notifications({
                "execution_id": "exec-004",
                "config_id": "cfg-1",
                "config_name": "测试",
                "status": "success",
                "summary": "完成",
            })
