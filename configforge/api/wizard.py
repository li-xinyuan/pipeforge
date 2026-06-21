from __future__ import annotations

import logging
import urllib.parse
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from configforge.core.pipeline import (
    dry_run,
    generate,
    infer_input,
    infer_output,
    init_scene,
)
from configforge.middleware.auth import require_role
from configforge.models.user import User, UserRole
from configforge.models.wizard import (
    ApiInferRequest,
    GenerateRequest,
    GenerateResponse,
    InputInferRequest,
    InputInferResponse,
    OutputInferRequest,
    OutputInferResponse,
    SceneInitRequest,
    SceneInitResponse,
)

if TYPE_CHECKING:
    from configforge.models.wizard import WizardState
from configforge.services.execution_service import (
    ExecutionContext,
    execute_with_progress,
)
from configforge.services.execution_service import (
    execute as execute_service,
)

router = APIRouter(tags=["向导"])
logger = logging.getLogger(__name__)

# Errors caused by user input (bad script, missing function, timeout, etc.)
from pipeforge.config.exceptions import CheckpointError

_USER_ERRORS = (ValueError, SyntaxError, TimeoutError, CheckpointError)


@router.post("/init-scene", summary="初始化场景", description="根据用户提供的场景信息初始化 Pipeline 配置。返回包含默认输入、输出和处理器的初始状态。", response_model=SceneInitResponse)
async def api_init_scene(req: SceneInitRequest):
    try:
        return init_scene(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("init-scene failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-input/{input_name}", summary="推断输入列", description="根据指定的输入名称和请求参数，自动推断数据源的列信息和样本值。支持 Excel、CSV、JSON 等文件格式。", response_model=InputInferResponse)
async def api_infer_input(input_name: str, req: InputInferRequest):
    try:
        return infer_input(input_name, req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-input failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-api-input/{input_name}", summary="推断 API 输入列", description="从 REST API 端点推断数据列信息。支持 GET/POST 请求、分页、自定义请求头和请求体。返回列名、样本值和建议的参数键。", response_model=InputInferResponse)
async def api_infer_api_input(input_name: str, req: ApiInferRequest):
    """Infer columns from a REST API endpoint."""
    try:
        from configforge.services.api_reader import read_api_info
        info = read_api_info(
            url=req.url,
            method=req.method,
            headers=req.headers,
            params=req.params,
            body=req.body,
            data_path=req.data_path,
            pagination=req.pagination,
            page_size=req.page_size,
            max_pages=req.max_pages,
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


@router.post("/infer-output", summary="推断输出配置", description="根据当前 Pipeline 状态自动推断输出配置，包括输出类型、文件格式和目标路径等。", response_model=OutputInferResponse)
async def api_infer_output(req: OutputInferRequest):
    try:
        return infer_output(req)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("infer-output failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", summary="生成 Pipeline 配置", description="根据向导状态生成完整的 Pipeline YAML 配置。包含输入源定义、数据加工步骤（SQL/Python）和输出目标。", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    try:
        return generate(req.state)
    except _USER_ERRORS as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run", summary="预览执行结果", description="预览 SQL 处理结果 — 只执行输入和加工阶段，返回中间表数据。不写入输出文件，用于验证 Pipeline 逻辑是否正确。")
async def api_dry_run(req: GenerateRequest, _user: User = Depends(require_role("editor", "admin"))):
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
async def api_execute(req: GenerateRequest, background_tasks: BackgroundTasks, _user: User = Depends(require_role("editor", "admin"))):
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


@router.post("/execute/stream", summary="流式执行配置", description="通过 SSE 流式返回 Pipeline 执行进度。客户端使用 fetch + ReadableStream 消费事件流。")
async def api_execute_stream(req: GenerateRequest, _user: User = Depends(require_role("editor", "admin"))):
    """流式执行 pipeline，通过 SSE 实时推送执行进度。"""
    context = ExecutionContext(config_id="", config_version=None)

    async def event_generator():
        async for event in execute_with_progress(req.state, context, sanitize_errors=False):
            yield event

    return EventSourceResponse(event_generator(), ping=15)


@router.get("/execute/stream", summary="流式执行配置（GET）", description="通过 SSE 流式返回 Pipeline 执行进度。使用 query parameter 传递 token 进行认证。需要先通过 POST /api/wizard/execute/stream/start 创建任务获取 task_id。")
async def api_execute_stream_get(
    request: Request,
    token: str = "",
    task_id: str = "",
):
    """GET SSE 端点 — 用于 EventSource API 连接。

    由于 EventSource 不支持自定义 header，通过 query parameter 传递 JWT token。
    """
    # --- JWT authentication via query parameter ---
    from configforge.middleware.jwt import decode_token, is_jwt_enabled
    from configforge.services.user_store import get_user_by_id

    if is_jwt_enabled():
        if not token:
            raise HTTPException(status_code=401, detail={"error": "未认证：缺少 token 参数", "code": "AUTH_REQUIRED"})
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail={"error": "令牌无效或已过期", "code": "AUTH_FAILED"})
        user = get_user_by_id(payload.get("sub", ""))
        if not user:
            raise HTTPException(status_code=401, detail={"error": "用户不存在", "code": "USER_NOT_FOUND"})
        if user.role not in (UserRole.editor, UserRole.admin):
            raise HTTPException(status_code=403, detail={"error": "权限不足", "code": "FORBIDDEN"})

    # Look up pending task
    if not task_id or task_id not in _pending_sse_tasks:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    state = _pending_sse_tasks.pop(task_id)
    context = ExecutionContext(config_id="", config_version=None)

    async def event_generator():
        async for event in execute_with_progress(state, context, sanitize_errors=False):
            yield event

    return EventSourceResponse(event_generator(), ping=15)


# In-memory store for pending SSE tasks (keyed by task_id)
_pending_sse_tasks: dict[str, WizardState] = {}


@router.post("/execute/stream/start", summary="创建流式执行任务", description="创建一个流式执行任务并返回 task_id，随后可通过 GET /api/wizard/execute/stream?task_id=xxx&token=xxx 连接 SSE 获取进度。")
async def api_execute_stream_start(req: GenerateRequest, _user: User = Depends(require_role("editor", "admin"))):
    """创建流式执行任务，返回 task_id 供 GET SSE 端点使用。"""
    task_id = uuid.uuid4().hex[:12]
    _pending_sse_tasks[task_id] = req.state

    # Auto-expire task after 5 minutes if not consumed
    import asyncio

    async def _expire_task():
        await asyncio.sleep(300)
        _pending_sse_tasks.pop(task_id, None)

    asyncio.create_task(_expire_task())

    return {"task_id": task_id}
