import os
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"预览执行失败: {e}")


@router.post("/execute")
async def api_execute(req: GenerateRequest):
    """执行 pipeline 并返回生成的输出文件。"""
    try:
        output_path = execute_pipeline(req.state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")
    filename = os.path.basename(output_path)
    media_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        output_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
