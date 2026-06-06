import os
import json
import uuid
import logging
import shutil
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from configforge.models.wizard import (
    SceneInitRequest,
    InputInferRequest,
    OutputInferRequest,
    GenerateRequest,
    ExecutionRecord,
)
from configforge.api.executions import (
    EXEC_DIR,
    _update_exec_index,
    _save_failed_execution,
)
from configforge.core.pipeline import (
    init_scene,
    infer_input,
    infer_output,
    generate,
    execute_pipeline,
    dry_run,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Errors caused by user input (bad script, missing function, timeout, etc.)
from pipeforge.config.exceptions import CheckpointError

_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, CheckpointError)


@router.post("/init-scene")
async def api_init_scene(req: SceneInitRequest):
    try:
        return init_scene(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("init-scene failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-input/{input_name}")
async def api_infer_input(input_name: str, req: InputInferRequest):
    try:
        return infer_input(input_name, req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-input failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-output")
async def api_infer_output(req: OutputInferRequest):
    try:
        return infer_output(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-output failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def api_generate(req: GenerateRequest):
    try:
        return generate(req.state)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run")
async def api_dry_run(req: GenerateRequest):
    """预览 SQL 处理结果 — 只执行输入和加工阶段，返回中间表数据。"""
    try:
        result = dry_run(req.state)
        return result
    except CheckpointError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "数据检查点未通过",
                "checks": [r.model_dump() for r in e.results],
            },
        )
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("dry-run failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def api_execute(req: GenerateRequest, background_tasks: BackgroundTasks):
    """执行 pipeline 并返回生成的输出文件。"""
    exec_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC).isoformat()

    inputs_summary = [
        {"name": inp.name, "plugin": inp.plugin, "param_key": inp.param_key}
        for inp in req.state.inputs
    ]
    processors_summary = [
        {"name": p.name, "plugin": p.plugin}
        for p in req.state.processors
    ]
    output_type = req.state.output.plugin if req.state.output else ""
    scene_name = req.state.scene.name or ""

    try:
        output_path = execute_pipeline(req.state)
    except _USER_ERRORS as e:
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id="",
            config_version=None,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=str(e),
        )
        raise HTTPException(status_code=422, detail=f"Pipeline execution failed: {e}")
    except Exception as e:
        logger.exception("pipeline execution failed")
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id="",
            config_version=None,
            scene_name=scene_name,
            inputs_summary=inputs_summary,
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")

    filename = os.path.basename(output_path)
    finished_at = datetime.now(UTC).isoformat()

    # Compute duration
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)

    # Move output to executions directory
    exec_output_dir = os.path.join(EXEC_DIR, exec_id)
    os.makedirs(exec_output_dir, exist_ok=True)
    exec_output_path = os.path.join(exec_output_dir, filename)
    shutil.move(output_path, exec_output_path)

    # Save execution record
    record = ExecutionRecord(
        id=exec_id,
        config_id="",
        config_version=None,
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

    # Schedule cleanup of the temp output directory after response is sent
    output_dir = os.path.dirname(output_path)
    background_tasks.add_task(lambda: shutil.rmtree(output_dir, ignore_errors=True))

    media_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        exec_output_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
