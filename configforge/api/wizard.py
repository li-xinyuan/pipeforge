import os
import json
import urllib.parse
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
from configforge.services.execution_service import (
    execute as execute_service,
    ExecutionContext,
)
from configforge.services.notifier.dispatcher import dispatch_notifications_async
from configforge.services.ai.auto_diagnose import auto_diagnose

router = APIRouter()
logger = logging.getLogger(__name__)

# Errors caused by user input (bad script, missing function, timeout, etc.)
from pipeforge.config.exceptions import CheckpointError

_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, CheckpointError)


@router.post("/init-scene", summary="初始化场景", description="根据用户提供的场景信息初始化 Pipeline 配置。返回包含默认输入、输出和处理器的初始状态。")
async def api_init_scene(req: SceneInitRequest):
    try:
        return init_scene(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("init-scene failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-input/{input_name}", summary="推断输入列", description="根据指定的输入名称和请求参数，自动推断数据源的列信息和样本值。支持 Excel、CSV、JSON 等文件格式。")
async def api_infer_input(input_name: str, req: InputInferRequest):
    try:
        return infer_input(input_name, req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-input failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-api-input/{input_name}", summary="推断 API 输入列", description="从 REST API 端点推断数据列信息。支持 GET/POST 请求、分页、自定义请求头和请求体。返回列名、样本值和建议的参数键。")
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


@router.post("/infer-output", summary="推断输出配置", description="根据当前 Pipeline 状态自动推断输出配置，包括输出类型、文件格式和目标路径等。")
async def api_infer_output(req: OutputInferRequest):
    try:
        return infer_output(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-output failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", summary="生成 Pipeline 配置", description="根据向导状态生成完整的 Pipeline YAML 配置。包含输入源定义、数据加工步骤（SQL/Python）和输出目标。")
async def api_generate(req: GenerateRequest):
    try:
        return generate(req.state)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run", summary="预览执行结果", description="预览 SQL 处理结果 — 只执行输入和加工阶段，返回中间表数据。不写入输出文件，用于验证 Pipeline 逻辑是否正确。")
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


@router.post("/execute", summary="执行 Pipeline", description="执行指定的 Pipeline 配置，返回生成的输出文件。支持 Excel 和 CSV 输出格式。若输出目标为数据库，则返回成功 JSON。")
async def api_execute(req: GenerateRequest, background_tasks: BackgroundTasks):
    """执行 pipeline 并返回生成的输出文件。"""
    context = ExecutionContext(config_id="", config_version=None)
    result = await execute_service(req.state, context, sanitize_errors=False)

    if result.status == "failed":
        if result.checks:
            raise HTTPException(status_code=422, detail={"message": "数据检查点未通过", "checks": result.checks})
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {result.error_message}")

    # Database output: no file generated, return success JSON
    if result.output_file_name is None:
        return JSONResponse({"status": "success", "message": "数据已写入目标数据库", "exec_id": result.exec_id})

    # Schedule cleanup of the temp output directory after response is sent
    # (output has already been moved by execution_service, no cleanup needed)

    media_type = "text/csv" if result.output_file_name.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    encoded_name = urllib.parse.quote(result.output_file_name)
    return FileResponse(
        result.output_path,
        media_type=media_type,
        filename=result.output_file_name,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
