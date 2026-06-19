"""Dispatcher: automatically send notifications after pipeline execution."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from configforge.api.notifications import (
    _load_notifications,
    _send_notification,
    add_history_entry,
)
from configforge.models.notification import NotificationHistoryEntry
from configforge.services.notifier.base import NotifyContext

logger = logging.getLogger(__name__)


def build_notify_context(execution_result: dict) -> NotifyContext:
    """Build a NotifyContext from a pipeline execution result dict."""
    return NotifyContext(
        execution_id=execution_result.get("execution_id", ""),
        config_name=execution_result.get("config_name", "未知配置"),
        status=execution_result.get("status", "unknown"),
        summary=execution_result.get("summary", ""),
        output_files=execution_result.get("output_files", []),
        started_at=execution_result.get("started_at", ""),
        finished_at=execution_result.get("finished_at", ""),
        error_message=execution_result.get("error_message"),
    )


def should_trigger(config, context: NotifyContext) -> bool:
    """Check if a notification config should trigger for this context."""
    if not config.enabled:
        return False
    if context.status == "success" and not config.trigger_on_success:
        return False
    if context.status == "failed" and not config.trigger_on_failure:
        return False
    if context.status == "anomaly" and not config.trigger_on_anomaly:
        return False
    return True


async def dispatch_notifications(execution_result: dict) -> None:
    """Dispatch notifications to all matching configs after pipeline execution.

    This is called as a fire-and-forget background task — errors are logged
    but do not affect the pipeline execution result.
    """
    context = build_notify_context(execution_result)
    configs = _load_notifications()

    for config in configs:
        if not should_trigger(config, context):
            continue

        # If config_ids is set, only trigger for matching pipeline config IDs
        if config.config_ids is not None:
            pipeline_config_id = execution_result.get("config_id", "")
            if pipeline_config_id and pipeline_config_id not in config.config_ids:
                continue

        try:
            result = await _send_notification(config, context)
            entry = NotificationHistoryEntry(
                id=str(uuid.uuid4())[:8],
                config_id=config.id,
                config_name=config.name,
                execution_id=context.execution_id,
                pipeline_config_name=context.config_name,
                status=context.status,
                notify_success=result.success,
                provider=result.provider,
                message=result.message,
                triggered_at=datetime.now(timezone.utc).isoformat(),
            )
            add_history_entry(entry)
        except Exception as exc:
            # Don't let notification failures affect anything
            logger.warning(f"Notification dispatch failed for config {config.id}: {exc}")


def dispatch_notifications_async(execution_result: dict) -> None:
    """Fire-and-forget wrapper: schedule dispatch in background."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(dispatch_notifications(execution_result))
    except RuntimeError:
        # No running loop — run synchronously (shouldn't happen in FastAPI)
        asyncio.run(dispatch_notifications(execution_result))
