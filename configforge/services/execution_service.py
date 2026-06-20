"""Unified Pipeline execution service.

Extracts the common execution logic from configs.py, wizard.py, and scheduler.py
into a single service, eliminating ~292 lines of duplicated code.
"""

import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Callable, Optional

from configforge.core.pipeline import execute_pipeline, PipelineTimeoutError
from configforge.models.wizard import ExecutionRecord, WizardState
from configforge.api.executions import (
    EXEC_DIR,
    _update_exec_index,
    _save_failed_execution,
    _sanitize_summary,
)
from configforge.services.notifier.dispatcher import dispatch_notifications_async
from configforge.services.ai.auto_diagnose import auto_diagnose
from configforge.utils.security import sanitize_connection_string
from pipeforge.config.exceptions import CheckpointError

logger = logging.getLogger(__name__)

_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, PipelineTimeoutError)


@dataclass
class ExecutionContext:
    """Context provided by the caller for pipeline execution."""
    config_id: str = ""
    config_version: Optional[int] = None
    scene_name: str = ""
    inputs_summary: list[dict] = field(default_factory=list)
    processors_summary: list[dict] = field(default_factory=list)
    output_type: str = ""


@dataclass
class ExecutionResult:
    """Result of a pipeline execution, used by callers to construct responses."""
    exec_id: str
    status: str  # "success" | "failed"
    started_at: str
    finished_at: str
    duration_ms: int
    output_path: Optional[str] = None
    output_file_name: Optional[str] = None
    error_message: Optional[str] = None
    checks: Optional[list[dict]] = None
    diagnosis: Optional[dict] = None


def _build_context_from_state(state: WizardState) -> ExecutionContext:
    """Build an ExecutionContext from a WizardState, extracting summaries."""
    return ExecutionContext(
        scene_name=state.scene.name or "",
        inputs_summary=[
            {"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key}
            for inp in state.inputs
        ],
        processors_summary=[
            {"name": p.name, "plugin": p.plugin}
            for p in state.processors
        ],
        output_type=state.output.plugin if state.output else "",
    )


async def execute(
    state: WizardState,
    context: ExecutionContext,
    *,
    sanitize_errors: bool = True,
    on_success: Optional[Callable[[], None]] = None,
    on_failed: Optional[Callable[[], None]] = None,
) -> ExecutionResult:
    """Execute a Pipeline and handle recording/notifications.

    Args:
        state: The prepared WizardState to execute.
        context: Execution context with config_id, summaries, etc.
                 Fields left empty will be auto-filled from state.
        sanitize_errors: Whether to sanitize connection strings in error messages.
        on_success: Optional callback on successful execution.
        on_failed: Optional callback on failed execution.

    Returns:
        ExecutionResult for the caller to construct HTTP response or log.
    """
    # Auto-fill missing context fields from state
    if not context.scene_name:
        context.scene_name = state.scene.name or ""
    if not context.inputs_summary:
        context.inputs_summary = [
            {"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key}
            for inp in state.inputs
        ]
    if not context.processors_summary:
        context.processors_summary = [
            {"name": p.name, "plugin": p.plugin}
            for p in state.processors
        ]
    if not context.output_type:
        context.output_type = state.output.plugin if state.output else ""

    exec_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC).isoformat()

    # --- Execute Pipeline ---
    try:
        output_path = execute_pipeline(state)
    except CheckpointError as e:
        return await _handle_failure(
            exec_id, started_at, context,
            error_message="数据检查点未通过",
            checks=[r.model_dump() for r in e.results],
            sanitize_errors=False,
            on_failed=on_failed,
        )
    except _USER_ERRORS as e:
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        return await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
            on_failed=on_failed,
        )
    except Exception as e:
        logger.exception("Pipeline execution failed")
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        return await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
            on_failed=on_failed,
        )

    # --- Success ---
    return _handle_success(
        exec_id, started_at, context, output_path,
        on_success=on_success,
    )


async def _handle_failure(
    exec_id: str,
    started_at: str,
    context: ExecutionContext,
    *,
    error_message: str,
    checks: list[dict] | None = None,
    sanitize_errors: bool = True,
    on_failed: Callable[[], None] | None = None,
) -> ExecutionResult:
    """Handle a failed pipeline execution: diagnose, record, notify."""
    finished_at = datetime.now(UTC).isoformat()

    # AI diagnosis
    diagnosis = None
    try:
        diagnosis = await auto_diagnose(
            yaml_text="",
            error_message=error_message,
            scene_name=context.scene_name,
            inputs_summary=context.inputs_summary,
            processors_summary=context.processors_summary,
        )
    except Exception as diag_exc:
        logger.warning("Auto-diagnosis failed: %s", diag_exc)

    # Save failed execution record
    _save_failed_execution(
        exec_id=exec_id,
        started_at=started_at,
        config_id=context.config_id,
        config_version=context.config_version,
        scene_name=context.scene_name,
        inputs_summary=context.inputs_summary,
        processors_summary=context.processors_summary,
        output_type=context.output_type,
        error_message=error_message,
        checks_summary=checks,
        diagnosis=diagnosis,
    )

    # Dispatch failure notification
    _dispatch_notification(
        exec_id=exec_id,
        context=context,
        status="failed",
        summary="数据检查点未通过" if checks else "Pipeline 执行失败",
        error_message=error_message,
        started_at=started_at,
        finished_at=finished_at,
    )

    if on_failed:
        on_failed()

    return ExecutionResult(
        exec_id=exec_id,
        status="failed",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=_calc_duration_ms(started_at, finished_at),
        error_message=error_message,
        checks=checks,
        diagnosis=diagnosis,
    )


def _handle_success(
    exec_id: str,
    started_at: str,
    context: ExecutionContext,
    output_path: str | None,
    *,
    on_success: Callable[[], None] | None = None,
) -> ExecutionResult:
    """Handle a successful pipeline execution: move output, record, notify."""
    finished_at = datetime.now(UTC).isoformat()
    duration_ms = _calc_duration_ms(started_at, finished_at)

    # Move output file to execution directory
    output_file_name = None
    exec_output_path = None
    if output_path:
        filename = os.path.basename(output_path)
        exec_output_dir = os.path.join(EXEC_DIR, exec_id)
        os.makedirs(exec_output_dir, exist_ok=True)
        exec_output_path = os.path.join(exec_output_dir, filename)
        shutil.move(output_path, exec_output_path)

        # Clean up intermediate output directory
        output_intermediate_dir = os.path.dirname(output_path)
        if os.path.isdir(output_intermediate_dir):
            shutil.rmtree(output_intermediate_dir, ignore_errors=True)

        output_file_name = filename

    # Save execution record
    record = ExecutionRecord(
        id=exec_id,
        config_id=context.config_id,
        config_version=context.config_version,
        scene_name=context.scene_name,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        inputs_summary=_sanitize_summary(context.inputs_summary),
        processors_summary=context.processors_summary,
        output_type=context.output_type,
        checks_summary=[],
        output_file_name=output_file_name,
    )

    exec_record_dir = os.path.join(EXEC_DIR, exec_id)
    os.makedirs(exec_record_dir, exist_ok=True)
    result_path = os.path.join(exec_record_dir, "result.json")
    with open(result_path, "w") as f:
        json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

    _update_exec_index(record)

    # Dispatch success notification
    _dispatch_notification(
        exec_id=exec_id,
        context=context,
        status="success",
        summary=f"输出文件: {output_file_name}" if output_file_name else "数据已写入目标数据库",
        output_files=[output_file_name] if output_file_name else [],
        started_at=started_at,
        finished_at=finished_at,
    )

    if on_success:
        on_success()

    return ExecutionResult(
        exec_id=exec_id,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        output_path=exec_output_path,
        output_file_name=output_file_name,
    )


def _dispatch_notification(
    *,
    exec_id: str,
    context: ExecutionContext,
    status: str,
    summary: str,
    started_at: str,
    finished_at: str,
    error_message: str | None = None,
    output_files: list[str] | None = None,
) -> None:
    """Dispatch execution notification (fire-and-forget)."""
    try:
        payload = {
            "execution_id": exec_id,
            "config_id": context.config_id,
            "config_name": context.scene_name,
            "status": status,
            "summary": summary,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        if error_message:
            payload["error_message"] = error_message
        if output_files:
            payload["output_files"] = output_files
        dispatch_notifications_async(payload)
    except Exception as notify_exc:
        logger.warning("Notification dispatch failed: %s", notify_exc)


def _calc_duration_ms(started_at: str, finished_at: str) -> int:
    """Calculate duration in milliseconds between two ISO timestamps."""
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    return int((end_dt - start_dt).total_seconds() * 1000)
