"""Scheduled execution for ConfigForge pipelines using APScheduler."""

import asyncio
import contextlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field

from configforge.utils.file_lock import write_json_locked
from configforge.utils.migration import ensure_schema_version, load_with_migration
from configforge.utils.paths import get_data_dir

logger = logging.getLogger(__name__)

DATA_DIR = get_data_dir()
SCHEDULES_PATH = os.path.join(DATA_DIR, "schedules.json")

_running_configs: set[str] = set()


class ScheduleConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str
    cron_expression: str  # e.g., "0 8 * * *" = every day at 8:00
    enabled: bool = True
    description: str = ""
    created_at: str = ""
    last_run_at: str | None = None
    last_run_status: str | None = None  # "success" | "failed"
    retry_count: int = 0        # 最大重试次数（0=不重试）
    retry_interval: int = 300   # 重试间隔（秒）


# ── Global scheduler instance ──

_scheduler: BackgroundScheduler | None = None


def _load_schedules() -> list[dict]:
    os.makedirs(DATA_DIR, exist_ok=True)
    data = load_with_migration(SCHEDULES_PATH, default={"schedules": []})
    if isinstance(data, list):
        return data
    return data.get("schedules", [])


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


# ── BackgroundScheduler 管理函数（不涉及持久化）──
# T-5E-04: 分离调度器管理和存储职责，让 SQL 后端也能注册任务


def _register_job(schedule_dict: dict) -> None:
    """注册一个调度任务到 BackgroundScheduler（不涉及持久化）。

    Args:
        schedule_dict: 包含 id, config_id, cron_expression, enabled 的字典
    """
    if not _scheduler:
        return
    if not schedule_dict.get("enabled", True):
        return
    _scheduler.add_job(
        _run_scheduled_pipeline,
        trigger=CronTrigger.from_crontab(schedule_dict["cron_expression"]),
        id=schedule_dict["id"],
        args=[schedule_dict["id"], schedule_dict["config_id"]],
        replace_existing=True,
        coalesce=True,      # 多次错过的触发合并为一次执行
        max_instances=1,    # 同一 job 不并发执行
    )


def _unregister_job(schedule_id: str) -> None:
    """从 BackgroundScheduler 移除一个任务（不涉及持久化）。"""
    if not _scheduler:
        return
    with contextlib.suppress(Exception):
        _scheduler.remove_job(schedule_id)


def _get_schedule_retry_config(schedule_id: str) -> tuple[int, int]:
    """Get retry_count and retry_interval for a schedule.

    T-5E-04: 优先从 store 层读取（支持 SQL 后端），fallback 到 schedules.json。
    """
    try:
        from configforge.storage import get_schedule_store
        store = get_schedule_store()
        schedules = store.list_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                return s.get("retry_count", 0), s.get("retry_interval", 300)
        return 0, 300
    except Exception:
        # Fallback: 读 schedules.json（JSON 后端兼容）
        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                return s.get("retry_count", 0), s.get("retry_interval", 300)
        return 0, 300


def _handle_retry(schedule_id: str, config_id: str, remaining_retries: int) -> None:
    """Handle retry logic after a scheduled execution failure.

    If remaining_retries > 0, schedule a retry. Otherwise, check if the
    schedule has retry_count configured and this was the initial execution
    (remaining_retries == 0 from the cron job), then schedule the first retry.
    """
    if remaining_retries > 0:
        # This is a retry that failed, schedule next retry
        _, retry_interval = _get_schedule_retry_config(schedule_id)
        _schedule_retry(schedule_id, config_id, remaining_retries - 1, retry_interval)
    else:
        # This was the initial execution (from cron job), check if retry is configured
        retry_count, retry_interval = _get_schedule_retry_config(schedule_id)
        if retry_count > 0:
            _schedule_retry(schedule_id, config_id, retry_count - 1, retry_interval)


def _run_scheduled_pipeline(schedule_id: str, config_id: str, remaining_retries: int = 0) -> None:
    """Job callback: load config state and execute pipeline.

    Args:
        schedule_id: The schedule ID.
        config_id: The config ID to execute.
        remaining_retries: Remaining retry count (0 = no more retries).
    """
    if config_id in _running_configs:
        logger.info("Config %s already running, skipping scheduled execution", config_id)
        return
    _running_configs.add(config_id)

    logger.info("Scheduled job fired: schedule=%s config=%s remaining_retries=%d", schedule_id, config_id, remaining_retries)

    # Import here to avoid circular imports at module level
    from configforge.models.wizard import WizardState
    from configforge.services.config_store import CONFIGS_DIR
    from configforge.services.execution_service import ExecutionContext
    from configforge.services.execution_service import execute as execute_service

    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
    if not os.path.exists(state_path):
        logger.error("Config state not found for scheduled execution: %s", config_id)
        _update_schedule_last_run(schedule_id, "failed")
        _handle_retry(schedule_id, config_id, remaining_retries)
        return

    with open(state_path, encoding="utf-8") as f:
        state_dict = json.load(f)

    # Migrate old format
    state_dict = ensure_schema_version(state_dict, state_path)

    # Remove internal fields that are not part of WizardState schema
    state_dict.pop("_saved_at", None)
    state_dict.pop("change_summary", None)
    state_dict.pop("schema_version", None)

    try:
        state = WizardState(**state_dict)
    except Exception as e:
        logger.error("Failed to parse config state for scheduled execution: %s", e)
        _update_schedule_last_run(schedule_id, "failed")
        _handle_retry(schedule_id, config_id, remaining_retries)
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
        from configforge.services.execution_store import save_failed_execution as _save_failed_execution
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
        _handle_retry(schedule_id, config_id, remaining_retries)
        return

    # Get config metadata for execution record
    from configforge.services.config_store import load_index
    index = load_index()
    entry = next((e for e in index if e.get("id") == config_id), None)
    config_version = entry.get("current_version") if entry else None

    context = ExecutionContext(
        config_id=config_id,
        config_version=config_version,
    )

    # Run async execute_service in sync context
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            execute_service(
                state, context,
                sanitize_errors=False,
                on_success=lambda: _update_schedule_last_run(schedule_id, "success"),
                on_failed=lambda: _update_schedule_last_run(schedule_id, "failed"),
            )
        )
    finally:
        _running_configs.discard(config_id)
        loop.close()

    if result.status == "failed":
        logger.error("Scheduled pipeline execution failed: %s", result.error_message)
        _handle_retry(schedule_id, config_id, remaining_retries)
    else:
        logger.info("Scheduled pipeline completed: exec_id=%s", result.exec_id)


def _update_schedule_last_run(schedule_id: str, status: str) -> None:
    """Update the last_run_at and last_run_status for a schedule.

    T-5E-04: 优先走 store 层（支持 SQL 后端），fallback 到 schedules.json。
    """
    try:
        from configforge.storage import get_schedule_store
        store = get_schedule_store()
        store.update_last_run(schedule_id, status)
    except Exception:
        # Fallback: 直接写 schedules.json（JSON 后端兼容）
        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                s["last_run_at"] = datetime.now(UTC).isoformat()
                s["last_run_status"] = status
                break
        _save_schedules(schedules)


def _schedule_retry(schedule_id: str, config_id: str, remaining_retries: int, retry_interval: int) -> None:
    """Schedule a one-time retry job after retry_interval seconds."""
    if not _scheduler:
        logger.warning("Scheduler not running, cannot schedule retry for schedule %s", schedule_id)
        return

    retry_job_id = f"{schedule_id}_retry_{uuid.uuid4().hex[:8]}"
    _scheduler.add_job(
        _run_scheduled_pipeline,
        trigger="date",
        run_date=datetime.now(UTC).timestamp() + retry_interval,
        id=retry_job_id,
        args=[schedule_id, config_id, remaining_retries],
        replace_existing=False,
    )
    logger.info(
        "Scheduled retry for schedule=%s config=%s remaining_retries=%d interval=%ds job_id=%s",
        schedule_id, config_id, remaining_retries, retry_interval, retry_job_id,
    )


# ── Public API ──

def add_schedule(config_id: str, cron_expression: str, description: str = "", retry_count: int = 0, retry_interval: int = 300) -> ScheduleConfig:
    """Add a new schedule and register it with the running scheduler."""
    _validate_cron(cron_expression)

    schedule = ScheduleConfig(
        config_id=config_id,
        cron_expression=cron_expression,
        description=description,
        created_at=datetime.now(UTC).isoformat(),
        retry_count=retry_count,
        retry_interval=retry_interval,
    )

    schedules = _load_schedules()
    schedules.append(schedule.model_dump())
    _save_schedules(schedules)

    _register_job(schedule.model_dump())

    return schedule


def remove_schedule(schedule_id: str) -> bool:
    """Remove a schedule by ID. Returns True if found and removed."""
    schedules = _load_schedules()
    new_schedules = [s for s in schedules if s.get("id") != schedule_id]
    if len(new_schedules) == len(schedules):
        return False

    _save_schedules(new_schedules)

    _unregister_job(schedule_id)

    return True


def list_schedules() -> list[ScheduleConfig]:
    """List all schedules."""
    schedules = _load_schedules()
    return [ScheduleConfig(**s) for s in schedules]


def update_schedule(schedule_id: str, cron_expression: str | None = None, description: str | None = None, retry_count: int | None = None, retry_interval: int | None = None) -> ScheduleConfig | None:
    """Update a schedule's cron expression, description, and/or retry settings."""
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
    if retry_count is not None:
        target["retry_count"] = retry_count
    if retry_interval is not None:
        target["retry_interval"] = retry_interval

    _save_schedules(schedules)

    # Re-register job with updated config (only if enabled — disabled schedules have no job)
    if target.get("enabled", True):
        _unregister_job(schedule_id)
        _register_job(target)

    return ScheduleConfig(**target)


def toggle_schedule(schedule_id: str) -> ScheduleConfig | None:
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

    if target["enabled"]:
        _register_job(target)
    else:
        _unregister_job(schedule_id)

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

    # T-5E-04: 从 store 层读取调度任务（支持 JSON 和 SQL 后端）
    try:
        from configforge.storage import get_schedule_store
        store = get_schedule_store()
        schedules = store.list_schedules()
    except Exception as e:
        logger.warning("Failed to load schedules from store, falling back to JSON: %s", e)
        schedules = _load_schedules()

    for s in schedules:
        if s.get("enabled", True):
            try:
                _register_job(s)
            except Exception as e:
                logger.error("Failed to register schedule %s: %s", s.get("id"), e)

    logger.info("Scheduler started with %d enabled schedules", sum(1 for s in schedules if s.get("enabled", True)))

    # Add daily backup job at 2:00 AM
    try:
        import logging as _logging

        from configforge.utils.backup import create_backup, save_backup_to_disk

        _backup_logger = _logging.getLogger("configforge.backup")

        def _run_daily_backup():
            try:
                filename, zip_bytes = create_backup()
                save_backup_to_disk(zip_bytes, filename)
                _backup_logger.info("Daily backup created: %s", filename)
            except Exception as e:
                _backup_logger.error("Daily backup failed: %s", e)

        _scheduler.add_job(
            _run_daily_backup,
            trigger=CronTrigger(hour=2, minute=0),
            id="daily_backup",
            replace_existing=True,
        )
        logger.info("Daily backup job scheduled at 02:00")
    except Exception as e:
        logger.warning("Failed to schedule daily backup: %s", e)


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shut down")
