import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from configforge.models.wizard import (
    SceneInitRequest,
    InputInferRequest,
    OutputInferRequest,
    GenerateRequest,
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
    return init_scene(req)


@router.post("/infer-input/{input_name}")
async def api_infer_input(input_name: str, req: InputInferRequest):
    return infer_input(input_name, req)


@router.post("/infer-output")
async def api_infer_output(req: OutputInferRequest):
    return infer_output(req)


@router.post("/generate")
async def api_generate(req: GenerateRequest):
    return generate(req.state)


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
async def api_execute(req: GenerateRequest):
    """执行 pipeline 并返回生成的输出文件。"""
    try:
        output_path = execute_pipeline(req.state)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=f"Pipeline execution failed: {e}")
    except Exception as e:
        logger.exception("pipeline execution failed")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")
    filename = os.path.basename(output_path)
    media_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        output_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
