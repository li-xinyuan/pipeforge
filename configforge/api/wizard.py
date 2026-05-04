from fastapi import APIRouter
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
