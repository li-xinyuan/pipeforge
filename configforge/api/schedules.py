"""API endpoints for schedule management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from configforge.scheduler import (
    add_schedule,
    remove_schedule,
    list_schedules,
    update_schedule,
    toggle_schedule,
    get_next_run_time,
)
from configforge.api.configs import _load_index

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    config_id: str
    cron_expression: str
    description: str = ""


class UpdateScheduleRequest(BaseModel):
    cron_expression: str | None = None
    description: str | None = None


@router.get("")
async def api_list_schedules():
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


@router.post("")
async def api_add_schedule(req: CreateScheduleRequest):
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
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return schedule.model_dump()


@router.put("/{schedule_id}")
async def api_update_schedule(schedule_id: str, req: UpdateScheduleRequest):
    """Update a schedule."""
    try:
        schedule = update_schedule(
            schedule_id=schedule_id,
            cron_expression=req.cron_expression,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if schedule is None:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    return schedule.model_dump()


@router.delete("/{schedule_id}")
async def api_delete_schedule(schedule_id: str):
    """Delete a schedule."""
    removed = remove_schedule(schedule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return {"ok": True}


@router.post("/{schedule_id}/toggle")
async def api_toggle_schedule(schedule_id: str):
    """Toggle a schedule's enabled state."""
    schedule = toggle_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return schedule.model_dump()
