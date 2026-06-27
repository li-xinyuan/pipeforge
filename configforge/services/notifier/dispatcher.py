"""Dispatcher: automatically send notifications after pipeline execution."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from configforge.models.notification import NotificationHistoryEntry
from configforge.services.notifier.base import NotifyContext
from configforge.services.notifier.sender import send_notification as _send_notification
from configforge.services.notifier.store import (
    add_history_entry,
    get_last_triggered_at,
)
from configforge.services.notifier.store import (
    load_notifications as _load_notifications,
)

logger = logging.getLogger(__name__)

# Default cooldown period (seconds) for duplicate notifications
DEFAULT_NOTIFICATION_COOLDOWN_SECONDS = 300  # 5 minutes

# In-memory frequency control: {(notification_config_id, pipeline_config_id, status): last_trigger_epoch}
# NOTE: Process-level cache used as a fast path. The authoritative cooldown
# source is the shared notification history file (see get_last_triggered_at),
# which works across workers and survives restarts.
_last_trigger_times: dict[tuple[str, str, str], float] = {}


def _parse_iso_timestamp(ts: str) -> float | None:
    """Parse an ISO timestamp string to epoch seconds. Returns None on failure."""
    if not ts:
        return None
    try:
        # Support both with and without timezone suffix 'Z'
        normalized = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
        dt = datetime.fromisoformat(normalized)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def build_notify_context(execution_result: dict) -> NotifyContext:
    """Build a NotifyContext from a pipeline execution result dict."""
    started_at = execution_result.get("started_at", "")
    finished_at = execution_result.get("finished_at", "")

    # Compute duration_seconds if not explicitly provided
    duration_seconds = execution_result.get("duration_seconds")
    if duration_seconds is None:
        duration_ms = execution_result.get("duration_ms")
        if duration_ms is not None:
            try:
                duration_seconds = float(duration_ms) / 1000.0
            except (TypeError, ValueError):
                duration_seconds = None
        elif started_at and finished_at:
            start_ts = _parse_iso_timestamp(started_at)
            end_ts = _parse_iso_timestamp(finished_at)
            if start_ts is not None and end_ts is not None:
                duration_seconds = max(0.0, end_ts - start_ts)

    # Extract error_type and stack_summary from error_message if available
    error_message = execution_result.get("error_message")
    error_type = execution_result.get("error_type")
    stack_summary = execution_result.get("stack_summary")

    return NotifyContext(
        execution_id=execution_result.get("execution_id", ""),
        config_name=execution_result.get("config_name", "未知配置"),
        status=execution_result.get("status", "unknown"),
        summary=execution_result.get("summary", ""),
        output_files=execution_result.get("output_files", []),
        started_at=started_at,
        finished_at=finished_at,
        error_message=error_message,
        duration_seconds=duration_seconds,
        row_count=execution_result.get("row_count"),
        error_type=error_type,
        stack_summary=stack_summary,
    )


def should_trigger(config, context: NotifyContext) -> bool:
    """Check if a notification config should trigger for this context."""
    if not config.enabled:
        return False
    return not (
        context.status == "success" and not config.trigger_on_success
        or context.status == "failed" and not config.trigger_on_failure
        or context.status == "anomaly" and not config.trigger_on_anomaly
    )


def _is_within_cooldown(
    notification_config_id: str,
    pipeline_config_id: str,
    status: str,
    cooldown_seconds: int = DEFAULT_NOTIFICATION_COOLDOWN_SECONDS,
) -> bool:
    """Check if a notification was recently sent for the same (config, pipeline, status) tuple.

    Returns True if within cooldown period (should skip), False otherwise.

    Two-layer lookup: an in-process cache (fast path) plus the shared
    notification history file (authoritative, works across workers).
    """
    key = (notification_config_id, pipeline_config_id, status)
    now = time.time()

    # 1. Fast path: in-process cache
    last = _last_trigger_times.get(key)
    if last is not None and (now - last) < cooldown_seconds:
        return True

    # 2. Authoritative path: shared history (covers other workers / restarts)
    history_last = get_last_triggered_at(notification_config_id, pipeline_config_id, status)
    if history_last is not None and (now - history_last) < cooldown_seconds:
        # Backfill the in-process cache so subsequent checks stay fast.
        _last_trigger_times[key] = history_last
        return True

    return False


def _record_trigger(
    notification_config_id: str,
    pipeline_config_id: str,
    status: str,
) -> None:
    """Record that a notification was triggered for frequency control."""
    key = (notification_config_id, pipeline_config_id, status)
    _last_trigger_times[key] = time.time()


def reset_frequency_control() -> None:
    """Clear all frequency control state. Mainly for testing."""
    _last_trigger_times.clear()


async def dispatch_notifications(execution_result: dict) -> None:
    """Dispatch notifications to all matching configs after pipeline execution.

    This is called as a fire-and-forget background task — errors are logged
    but do not affect the pipeline execution result.

    Includes frequency control: if a notification for the same (config, pipeline, status)
    was sent within the cooldown period (default 5 minutes), it will be skipped.
    """
    context = build_notify_context(execution_result)
    configs = _load_notifications()
    pipeline_config_id = execution_result.get("config_id", "")

    for config in configs:
        if not should_trigger(config, context):
            continue

        # If config_ids is set, only trigger for matching pipeline config IDs
        if config.config_ids is not None and pipeline_config_id and pipeline_config_id not in config.config_ids:
            continue

        # Frequency control: skip if within cooldown
        if _is_within_cooldown(config.id, pipeline_config_id, context.status):
            logger.info(
                "Notification skipped due to cooldown: config=%s pipeline=%s status=%s",
                config.id, pipeline_config_id, context.status,
            )
            continue

        try:
            result = await _send_notification(config, context)
            # Record trigger time for frequency control (only if send was attempted)
            _record_trigger(config.id, pipeline_config_id, context.status)
            entry = NotificationHistoryEntry(
                id=str(uuid.uuid4())[:8],
                config_id=config.id,
                config_name=config.name,
                execution_id=context.execution_id,
                pipeline_config_name=context.config_name,
                pipeline_config_id=pipeline_config_id,
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
