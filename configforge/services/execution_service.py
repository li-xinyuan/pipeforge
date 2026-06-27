"""Unified Pipeline execution service.

Extracts the common execution logic from configs.py, wizard.py, and scheduler.py
into a single service, eliminating ~292 lines of duplicated code.
"""

import asyncio
import json
import logging
import os
import shutil
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from configforge.api.executions import (
    EXEC_DIR,
    _sanitize_summary,
    _save_failed_execution,
    _update_exec_index,
)
from configforge.core.pipeline import PipelineTimeoutError, _prepare_execution, execute_pipeline
from configforge.models.wizard import ExecutionRecord, WizardState
from configforge.services.ai.auto_diagnose import auto_diagnose
from configforge.services.notifier.dispatcher import dispatch_notifications_async
from configforge.utils.metrics import record_pipeline_execution, active_connections, configs_total
from configforge.utils.security import sanitize_connection_string
from pipeforge.config.exceptions import CheckpointError

logger = logging.getLogger(__name__)

_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, PipelineTimeoutError)


@dataclass
class ExecutionContext:
    """Context provided by the caller for pipeline execution."""
    config_id: str = ""
    config_version: int | None = None
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
    output_path: str | None = None
    output_file_name: str | None = None
    error_message: str | None = None
    checks: list[dict] | None = None
    diagnosis: dict | None = None


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
    on_success: Callable[[], None] | None = None,
    on_failed: Callable[[], None] | None = None,
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
    active_connections.inc()
    try:
        output_path = execute_pipeline(state)
    except CheckpointError as e:
        active_connections.dec()
        return await _handle_failure(
            exec_id, started_at, context,
            error_message="数据检查点未通过",
            checks=[r.model_dump() for r in e.results],
            sanitize_errors=False,
            on_failed=on_failed,
        )
    except _USER_ERRORS as e:
        active_connections.dec()
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        return await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
            on_failed=on_failed,
            error_type=type(e).__name__,
        )
    except Exception as e:
        active_connections.dec()
        logger.exception("Pipeline execution failed")
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        return await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
            on_failed=on_failed,
            error_type=type(e).__name__,
        )

    # --- Success ---
    active_connections.dec()
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
    error_type: str | None = None,
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
        duration_ms=_calc_duration_ms(started_at, finished_at),
        error_type=error_type,
    )

    if on_failed:
        on_failed()

    # Record pipeline execution metrics
    duration_ms = _calc_duration_ms(started_at, finished_at)
    record_pipeline_execution("failed", duration_ms / 1000.0)

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

    # Record pipeline execution metrics
    record_pipeline_execution("success", duration_ms / 1000.0)

    # Dispatch success notification
    _dispatch_notification(
        exec_id=exec_id,
        context=context,
        status="success",
        summary=f"输出文件: {output_file_name}" if output_file_name else "数据已写入目标数据库",
        output_files=[output_file_name] if output_file_name else [],
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
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
    duration_ms: int | None = None,
    row_count: int | None = None,
    error_type: str | None = None,
) -> None:
    """Dispatch execution notification (fire-and-forget).

    Enhanced (T-5D-04): includes duration_ms, row_count, error_type for
    richer notification templates.
    """
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
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        if row_count is not None:
            payload["row_count"] = row_count
        if error_type:
            payload["error_type"] = error_type
        dispatch_notifications_async(payload)
    except Exception as notify_exc:
        logger.warning("Notification dispatch failed: %s", notify_exc)


def _calc_duration_ms(started_at: str, finished_at: str) -> int:
    """Calculate duration in milliseconds between two ISO timestamps."""
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    return int((end_dt - start_dt).total_seconds() * 1000)


async def execute_with_progress(
    state: WizardState,
    context: ExecutionContext,
    *,
    sanitize_errors: bool = True,
) -> AsyncIterator[dict]:
    """Execute a Pipeline with real-time progress events via SSE.

    Yields SSE event dicts with keys: event, data (JSON string).
    Events emitted:
      - start: execution begins
      - input_start / input_done: each input source
      - processor_start / processor_done: each processor
      - output_start / output_done: output phase
      - complete: execution finished successfully
      - error: execution failed
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

    yield {"event": "start", "data": json.dumps({"config_id": context.config_id, "exec_id": exec_id})}

    active_connections.inc()
    try:
        # --- Prepare execution (runs sync code in thread) ---
        exec_state, tmp_dir, yaml_path, params = await asyncio.to_thread(
            _prepare_execution, state, False
        )

        is_db_output = (
            exec_state.output is not None
            and exec_state.output.plugin == "database"
        )

        from pipeforge.core.context import Context, Logger
        from pipeforge.core.engine import PipelineEngine
        from pipeforge.core.sqlite import SQLiteManager

        engine = PipelineEngine(yaml_path)

        # Build a shared context for all phases
        db = SQLiteManager()
        ctx = Context(
            db=db,
            params=params,
            yaml_dir=str(os.path.dirname(os.path.abspath(yaml_path))),
            scene_name=engine.config.scene.name,
            logger=Logger(log_dir=None),
        )

        try:
            # --- Input phase ---
            for inp_spec in engine.config.inputs:
                yield {
                    "event": "input_start",
                    "data": json.dumps({"stage": "input", "name": inp_spec.name}),
                }
                stats = await asyncio.to_thread(engine._execute_input, inp_spec, ctx)
                rows = stats.rows_loaded if stats else 0
                ctx.result.inputs[inp_spec.name] = stats
                yield {
                    "event": "input_done",
                    "data": json.dumps({"stage": "input", "name": inp_spec.name, "rows": rows}),
                }

            # --- Processor phase ---
            if engine.config.processors:
                input_tables = {inp.table for inp in engine.config.inputs}
                sorted_processors = engine._topological_sort(engine.config.processors, input_tables)
                for proc_spec in sorted_processors:
                    yield {
                        "event": "processor_start",
                        "data": json.dumps({"stage": "processor", "name": proc_spec.name}),
                    }
                    stats = await asyncio.to_thread(engine._execute_processor, proc_spec, ctx)
                    ctx.result.processors.append(stats)
                    tables_created = stats.tables_created if stats else []
                    yield {
                        "event": "processor_done",
                        "data": json.dumps({"stage": "processor", "name": proc_spec.name, "tables_created": tables_created}),
                    }

                    if proc_spec.checkpoints:
                        from pipeforge.core.checkpoints import execute_checks
                        default_table = proc_spec.output_tables[0] if proc_spec.output_tables else ""
                        check_results = execute_checks(proc_spec.checkpoints, ctx.db, default_table)
                        ctx.result.checks.extend(check_results)
                        if not all(r.passed for r in check_results):
                            raise CheckpointError(results=check_results)

            # --- Output phase ---
            if engine.config.output is not None:
                yield {
                    "event": "output_start",
                    "data": json.dumps({"stage": "output"}),
                }
                stats = await asyncio.to_thread(engine._execute_output, engine.config.output, ctx)
                ctx.result.output = stats
                rows_written = stats.rows_written if stats else 0
                yield {
                    "event": "output_done",
                    "data": json.dumps({"stage": "output", "rows": rows_written}),
                }

        finally:
            ctx.logger.close()
            db.close()

        # --- Determine output path ---
        output_path = ctx.output_path if ctx.output_path else None

        if is_db_output:
            output_path = None
            shutil.rmtree(tmp_dir, ignore_errors=True)
        elif not output_path or not os.path.exists(output_path):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise RuntimeError("Pipeline executed but no output file was generated")

        # Handle success using existing logic
        exec_result = _handle_success(
            exec_id, started_at, context, output_path,
        )

        active_connections.dec()
        yield {
            "event": "complete",
            "data": json.dumps({
                "status": "success",
                "exec_id": exec_result.exec_id,
                "output_file_name": exec_result.output_file_name,
                "duration_ms": exec_result.duration_ms,
            }),
        }

    except CheckpointError as e:
        active_connections.dec()
        result = await _handle_failure(
            exec_id, started_at, context,
            error_message="数据检查点未通过",
            checks=[r.model_dump() for r in e.results],
            sanitize_errors=False,
        )
        yield {
            "event": "error",
            "data": json.dumps({
                "message": result.error_message,
                "checks": result.checks,
                "diagnosis": result.diagnosis,
            }),
        }
    except _USER_ERRORS as e:
        active_connections.dec()
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        result = await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
        )
        yield {
            "event": "error",
            "data": json.dumps({
                "message": result.error_message,
                "diagnosis": result.diagnosis,
            }),
        }
    except Exception as e:
        active_connections.dec()
        logger.exception("Pipeline execution failed (SSE)")
        error_msg = sanitize_connection_string(str(e)) if sanitize_errors else str(e)
        result = await _handle_failure(
            exec_id, started_at, context,
            error_message=error_msg,
            sanitize_errors=False,
        )
        yield {
            "event": "error",
            "data": json.dumps({
                "message": result.error_message,
                "diagnosis": result.diagnosis,
            }),
        }
