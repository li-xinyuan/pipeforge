"""API endpoints for schedule management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from configforge.api.configs import _load_index
from configforge.middleware.auth import require_role
from configforge.models.user import User
from configforge.scheduler import (
    add_schedule,
    get_next_run_time,
    list_schedules,
    remove_schedule,
    toggle_schedule,
    update_schedule,
)
from configforge.utils.security import validate_id

router = APIRouter(prefix="/api/schedules", tags=["调度管理"])


class CreateScheduleRequest(BaseModel):
    config_id: str
    cron_expression: str
    description: str = ""
    retry_count: int = 0
    retry_interval: int = 300


class UpdateScheduleRequest(BaseModel):
    cron_expression: str | None = None
    description: str | None = None
    retry_count: int | None = None
    retry_interval: int | None = None


@router.get("", summary="获取调度列表", description="获取所有定时调度任务列表，包含关联的配置名称和下次执行时间。")
async def api_list_schedules(_user: User = Depends(require_role("viewer", "editor", "admin"))):
    """List all schedules with config name and next run time."""
    schedules = list_schedules()
    index = _load_index()
    config_map = {e.get("id"): e for e in index}

    result = []
    for s in schedules:
        entry = config_map.get(s.config_id, {})
        next_run = get_next_run_time(s.id)
        result.append({
            **s.model_dump(),
            "config_name": entry.get("scene_name", "未知配置"),
            "next_run_time": next_run,
        })
    return result


@router.post("", summary="创建调度任务", description="为指定配置创建定时调度任务。需要提供配置 ID、Cron 表达式和可选的描述。支持配置重试次数和重试间隔。")
async def api_add_schedule(req: CreateScheduleRequest, _user: User = Depends(require_role("editor", "admin"))):
    """Add a new schedule."""
    # Verify config exists
    index = _load_index()
    if not any(e.get("id") == req.config_id for e in index):
        raise HTTPException(status_code=404, detail="配置不存在")

    try:
        schedule = add_schedule(
            config_id=req.config_id,
            cron_expression=req.cron_expression,
            description=req.description,
            retry_count=req.retry_count,
            retry_interval=req.retry_interval,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return schedule.model_dump()


@router.put("/{schedule_id}", summary="更新调度任务", description="更新指定调度任务的配置。支持部分更新，可修改 Cron 表达式、描述、重试次数和重试间隔。")
async def api_update_schedule(schedule_id: str, req: UpdateScheduleRequest, _user: User = Depends(require_role("editor", "admin"))):
    """Update a schedule."""
    validate_id(schedule_id, "schedule_id")
    try:
        schedule = update_schedule(
            schedule_id=schedule_id,
            cron_expression=req.cron_expression,
            description=req.description,
            retry_count=req.retry_count,
            retry_interval=req.retry_interval,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if schedule is None:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    return schedule.model_dump()


@router.delete("/{schedule_id}", summary="删除调度任务", description="删除指定的定时调度任务。操作不可撤销，关联的配置不会被删除。")
async def api_delete_schedule(schedule_id: str, _user: User = Depends(require_role("editor", "admin"))):
    """Delete a schedule."""
    validate_id(schedule_id, "schedule_id")
    removed = remove_schedule(schedule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return {"ok": True}


@router.post("/{schedule_id}/toggle", summary="切换调度启用状态", description="切换指定调度任务的启用/禁用状态。禁用后调度任务将暂停执行，但不会删除。")
async def api_toggle_schedule(schedule_id: str, _user: User = Depends(require_role("editor", "admin"))):
    """Toggle a schedule's enabled state."""
    validate_id(schedule_id, "schedule_id")
    schedule = toggle_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return schedule.model_dump()
