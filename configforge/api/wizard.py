import os
import json
import uuid
import logging
import shutil
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
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
    _sanitize_summary,
)
from configforge.core.pipeline import (
    init_scene,
    infer_input,
    infer_output,
    generate,
    execute_pipeline,
    dry_run,
)
from configforge.services.notifier.dispatcher import dispatch_notifications_async
from configforge.services.ai.auto_diagnose import auto_diagnose

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


@router.post("/infer-api-input/{input_name}")
async def api_infer_api_input(input_name: str, req: dict):
    """Infer columns from a REST API endpoint."""
    try:
        from configforge.services.api_reader import read_api_info
        info = read_api_info(
            url=req.get("url", ""),
            method=req.get("method", "GET"),
            headers=req.get("headers", {}),
            params=req.get("params", {}),
            body=req.get("body"),
            data_path=req.get("data_path", ""),
            pagination=req.get("pagination", "none"),
            page_size=req.get("page_size", 100),
            max_pages=req.get("max_pages", 10),
        )
        from configforge.models.wizard import InputInferResponse
        # Build per-column sample values from sample_rows
        col_samples: dict[str, list[str]] = {c: [] for c in info["columns"]}
        for row in info["sample_rows"]:
            for idx, c in enumerate(info["columns"]):
                if idx < len(row) and len(col_samples[c]) < 3:
                    col_samples[c].append(str(row[idx]))

        return InputInferResponse(
            columns=[
                {"name": c, "sample_values": col_samples[c]}
                for c in info["columns"]
            ],
            suggested_table=input_name,
            suggested_param_key=f"{input_name}_api",
        )
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-api-input failed")
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
        error_msg = str(e)
        diagnosis = await auto_diagnose(
            yaml_text="", error_message=error_msg, scene_name=scene_name,
            inputs_summary=inputs_summary, processors_summary=processors_summary,
        )
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id="",
            config_version=None,
            scene_name=scene_name,
            inputs_summary=_sanitize_summary(inputs_summary),
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=error_msg,
            diagnosis=diagnosis,
        )
        dispatch_notifications_async({
            "execution_id": exec_id,
            "config_id": "",
            "config_name": scene_name,
            "status": "failed",
            "summary": "Pipeline 执行失败",
            "error_message": error_msg,
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
        })
        raise HTTPException(status_code=422, detail=f"Pipeline execution failed: {e}")
    except Exception as e:
        logger.exception("pipeline execution failed")
        error_msg = str(e)
        diagnosis = await auto_diagnose(
            yaml_text="", error_message=error_msg, scene_name=scene_name,
            inputs_summary=inputs_summary, processors_summary=processors_summary,
        )
        _save_failed_execution(
            exec_id=exec_id,
            started_at=started_at,
            config_id="",
            config_version=None,
            scene_name=scene_name,
            inputs_summary=_sanitize_summary(inputs_summary),
            processors_summary=processors_summary,
            output_type=output_type,
            error_message=error_msg,
            diagnosis=diagnosis,
        )
        dispatch_notifications_async({
            "execution_id": exec_id,
            "config_id": "",
            "config_name": scene_name,
            "status": "failed",
            "summary": "Pipeline 执行异常",
            "error_message": error_msg,
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")

    finished_at = datetime.now(UTC).isoformat()
    start_dt = datetime.fromisoformat(started_at)
    end_dt = datetime.fromisoformat(finished_at)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)

    # Database output: no file generated, return success JSON
    if output_path is None:
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
            output_file_name=None,
        )
        result_path = os.path.join(EXEC_DIR, exec_id)
        os.makedirs(result_path, exist_ok=True)
        with open(os.path.join(result_path, "result.json"), "w") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)
        _update_exec_index(record)
        # Dispatch notifications
        dispatch_notifications_async({
            "execution_id": exec_id,
            "config_id": "",
            "config_name": scene_name,
            "status": "success",
            "summary": f"数据已写入目标数据库",
            "started_at": started_at,
            "finished_at": finished_at,
        })
        return JSONResponse({"status": "success", "message": "数据已写入目标数据库", "exec_id": exec_id})

    filename = os.path.basename(output_path)

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

    # Dispatch notifications
    dispatch_notifications_async({
        "execution_id": exec_id,
        "config_id": "",
        "config_name": scene_name,
        "status": "success",
        "summary": f"输出文件: {filename}",
        "output_files": [filename],
        "started_at": started_at,
        "finished_at": finished_at,
    })

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
