"""Scheduled execution for ConfigForge pipelines using APScheduler."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, UTC
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field

from configforge.utils.file_lock import read_json_locked, write_json_locked

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
SCHEDULES_PATH = os.path.join(DATA_DIR, "schedules.json")


class ScheduleConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str
    cron_expression: str  # e.g., "0 8 * * *" = every day at 8:00
    enabled: bool = True
    description: str = ""
    created_at: str = ""
    last_run_at: str | None = None
    last_run_status: str | None = None  # "success" | "failed"


# ── Global scheduler instance ──

_scheduler: BackgroundScheduler | None = None


def _load_schedules() -> list[dict]:
    if not os.path.exists(SCHEDULES_PATH):
        return []
    return read_json_locked(SCHEDULES_PATH)


def _save_schedules(data: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    write_json_locked(SCHEDULES_PATH, data)


def _validate_cron(expr: str) -> None:
    """Validate a 5-field cron expression using APScheduler's CronTrigger."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression: expected 5 fields (minute hour day month weekday), got {len(parts)}"
        )
    # CronTrigger.from_crontab will raise if the expression is invalid
    CronTrigger.from_crontab(expr)


def _run_scheduled_pipeline(schedule_id: str, config_id: str) -> None:
    """Job callback: load config state and execute pipeline."""
    logger.info("Scheduled job fired: schedule=%s config=%s", schedule_id, config_id)

    # Import here to avoid circular imports at module level
    from configforge.api.configs import CONFIGS_DIR
    from configforge.core.pipeline import execute_pipeline
    from configforge.models.wizard import WizardState
    from configforge.api.executions import _update_exec_index, _save_failed_execution

    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    if not os.path.exists(state_path):
        logger.error("Config state not found for scheduled execution: %s", config_id)
        _update_schedule_last_run(schedule_id, "failed")
        return

    with open(state_path, "r", encoding="utf-8") as f:
        state_dict = json.load(f)

    # Migrate old format
    from configforge.api.configs import _migrate_state_dict
    _migrate_state_dict(state_dict)

    # Remove internal fields that are not part of WizardState schema
    state_dict.pop("_saved_at", None)
    state_dict.pop("change_summary", None)

    try:
        state = WizardState(**state_dict)
    except Exception as e:
        logger.error("Failed to parse config state for scheduled execution: %s", e)
        _update_schedule_last_run(schedule_id, "failed")
        return

    # Check for file-based inputs without file_id (will fail at execution time)
    file_inputs_without_file = [
        inp for inp in state.inputs
        if hasattr(inp.config, 'type') and inp.config.type != "database"
        and not inp.file_id
    ]
    if file_inputs_without_file:
        names = ", ".join(inp.name for inp in file_inputs_without_file)
        error_msg = f"配置包含文件输入源但文件未上传（{names}），定时任务无法自动上传文件，请改用数据库输入源"
        logger.error("Scheduled execution skipped: %s", error_msg)
        exec_id = uuid.uuid4().hex[:8]
        started_at = datetime.now(UTC).isoformat()
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id=config_id,
            config_version=None,
            scene_name=state.scene.name or "",
            inputs_summary=[{"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key} for inp in state.inputs],
            processors_summary=[{"name": p.name, "plugin": p.plugin} for p in state.processors],
            output_type=state.output.plugin if state.output else "",
            error_message=error_msg,
        )
        _update_schedule_last_run(schedule_id, "failed")
        return

    # Get config metadata for execution record
    from configforge.api.configs import _load_index
    index = _load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    config_version = entry.get("current_version") if entry else None
    scene_name = state.scene.name or ""

    exec_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC).isoformat()

    inputs_summary = [
        {"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key}
        for inp in state.inputs
    ]
    processors_summary = [
        {"name": p.name, "plugin": p.plugin}
        for p in state.processors
    ]
    output_type = state.output.plugin if state.output else ""

    try:
        output_path = execute_pipeline(state)
        _update_schedule_last_run(schedule_id, "success")
    except Exception as e:
        logger.exception("Scheduled pipeline execution failed: %s", e)
        # Auto-diagnose using AI (same as manual execution)
        diagnosis = None
        try:
            from configforge.services.ai.auto_diagnose import auto_diagnose
            loop = asyncio.new_event_loop()
            try:
                diagnosis = loop.run_until_complete(auto_diagnose(
                    yaml_text="",
                    error_message=str(e),
                    scene_name=scene_name,
                    inputs_summary=inputs_summary,
                    processors_summary=processors_summary,
                ))
            finally:
                loop.close()
        except Exception as diag_exc:
            logger.warning("Auto-diagnosis failed for scheduled pipeline: %s", diag_exc)

        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id=config_id,
            config_version=config_version,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=str(e),
            diagnosis=diagnosis,
        )
        _update_schedule_last_run(schedule_id, "failed")

        # Dispatch notification
        try:
            from configforge.services.notifier.dispatcher import dispatch_notifications_async
            dispatch_notifications_async(
                config_id=config_id,
                status="failed",
                config_name=scene_name,
                error_message=str(e),
                duration_ms=0,
            )
        except Exception as notify_exc:
            logger.warning("Notification dispatch failed: %s", notify_exc)
        return

    # Save successful execution record (same logic as configs.py execute_config)
    import shutil
    from configforge.api.executions import EXEC_DIR
    from configforge.models.wizard import ExecutionRecord

    # Handle database output (output_path is None) vs file output
    if output_path is None:
        filename = None
    else:
        filename = os.path.basename(output_path)
    finished_at = datetime.now(UTC).isoformat()
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)

    exec_output_dir = os.path.join(EXEC_DIR, exec_id)
    os.makedirs(exec_output_dir, exist_ok=True)

    if output_path is not None and filename:
        exec_output_path = os.path.join(exec_output_dir, filename)
        shutil.move(output_path, exec_output_path)
        output_intermediate_dir = os.path.dirname(output_path)
        if os.path.isdir(output_intermediate_dir):
            shutil.rmtree(output_intermediate_dir, ignore_errors=True)

    record = ExecutionRecord(
        id=exec_id,
        config_id=config_id,
        config_version=config_version,
        scene_name=scene_name,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        inputs_summary=inputs_summary,
        processors_summary=processors_summary,
        output_type=output_type,
        checks_summary=[],
        output_file_name=filename,
    )

    result_path = os.path.join(exec_output_dir, "result.json")
    with open(result_path, "w") as f:
        json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

    _update_exec_index(record)
    logger.info("Scheduled pipeline completed: exec_id=%s", exec_id)

    # Dispatch notification on success
    try:
        from configforge.services.notifier.dispatcher import dispatch_notifications_async
        dispatch_notifications_async(
            config_id=config_id,
            status="success",
            config_name=scene_name,
            duration_ms=duration_ms,
        )
    except Exception as notify_exc:
        logger.warning("Notification dispatch failed: %s", notify_exc)


def _update_schedule_last_run(schedule_id: str, status: str) -> None:
    """Update the last_run_at and last_run_status for a schedule."""
    schedules = _load_schedules()
    for s in schedules:
        if s.get("id") == schedule_id:
            s["last_run_at"] = datetime.now(UTC).isoformat()
            s["last_run_status"] = status
            break
    _save_schedules(schedules)


# ── Public API ──

def add_schedule(config_id: str, cron_expression: str, description: str = "") -> ScheduleConfig:
    """Add a new schedule and register it with the running scheduler."""
    _validate_cron(cron_expression)

    schedule = ScheduleConfig(
        config_id=config_id,
        cron_expression=cron_expression,
        description=description,
        created_at=datetime.now(UTC).isoformat(),
    )

    schedules = _load_schedules()
    schedules.append(schedule.model_dump())
    _save_schedules(schedules)

    if _scheduler and schedule.enabled:
        _scheduler.add_job(
            _run_scheduled_pipeline,
            trigger=CronTrigger.from_crontab(schedule.cron_expression),
            id=schedule.id,
            args=[schedule.id, schedule.config_id],
            replace_existing=True,
        )

    return schedule


def remove_schedule(schedule_id: str) -> bool:
    """Remove a schedule by ID. Returns True if found and removed."""
    schedules = _load_schedules()
    new_schedules = [s for s in schedules if s.get("id") != schedule_id]
    if len(new_schedules) == len(schedules):
        return False

    _save_schedules(new_schedules)

    if _scheduler:
        try:
            _scheduler.remove_job(schedule_id)
        except Exception:
            pass  # Job may not exist if disabled

    return True


def list_schedules() -> list[ScheduleConfig]:
    """List all schedules."""
    schedules = _load_schedules()
    return [ScheduleConfig(**s) for s in schedules]


def update_schedule(schedule_id: str, cron_expression: str | None = None, description: str | None = None) -> Optional[ScheduleConfig]:
    """Update a schedule's cron expression and/or description."""
    schedules = _load_schedules()
    target = None
    for s in schedules:
        if s.get("id") == schedule_id:
            target = s
            break

    if target is None:
        return None

    if cron_expression is not None:
        _validate_cron(cron_expression)
        target["cron_expression"] = cron_expression
    if description is not None:
        target["description"] = description

    _save_schedules(schedules)

    # Re-register job if scheduler is running and schedule is enabled
    if _scheduler and target.get("enabled", True):
        try:
            _scheduler.remove_job(schedule_id)
        except Exception:
            pass
        _scheduler.add_job(
            _run_scheduled_pipeline,
            trigger=CronTrigger.from_crontab(target["cron_expression"]),
            id=schedule_id,
            args=[schedule_id, target["config_id"]],
            replace_existing=True,
        )

    return ScheduleConfig(**target)


def toggle_schedule(schedule_id: str) -> Optional[ScheduleConfig]:
    """Toggle a schedule's enabled state."""
    schedules = _load_schedules()
    target = None
    for s in schedules:
        if s.get("id") == schedule_id:
            target = s
            break

    if target is None:
        return None

    target["enabled"] = not target.get("enabled", True)
    _save_schedules(schedules)

    if _scheduler:
        if target["enabled"]:
            _scheduler.add_job(
                _run_scheduled_pipeline,
                trigger=CronTrigger.from_crontab(target["cron_expression"]),
                id=schedule_id,
                args=[schedule_id, target["config_id"]],
                replace_existing=True,
            )
        else:
            try:
                _scheduler.remove_job(schedule_id)
            except Exception:
                pass

    return ScheduleConfig(**target)


def get_next_run_time(schedule_id: str) -> str | None:
    """Get the next run time for a scheduled job."""
    if not _scheduler:
        return None
    job = _scheduler.get_job(schedule_id)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


def start_scheduler() -> None:
    """Start the background scheduler and register all enabled schedules."""
    global _scheduler

    if _scheduler is not None:
        return  # Already running

    _scheduler = BackgroundScheduler()
    _scheduler.start()

    # Register all enabled schedules from storage
    schedules = _load_schedules()
    for s in schedules:
        if s.get("enabled", True):
            try:
                _scheduler.add_job(
                    _run_scheduled_pipeline,
                    trigger=CronTrigger.from_crontab(s["cron_expression"]),
                    id=s["id"],
                    args=[s["id"], s["config_id"]],
                    replace_existing=True,
                )
            except Exception as e:
                logger.error("Failed to register schedule %s: %s", s.get("id"), e)

    logger.info("Scheduler started with %d enabled schedules", sum(1 for s in schedules if s.get("enabled", True)))


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shut down")
