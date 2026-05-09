import asyncio
import time
from fastapi import APIRouter, HTTPException
from configforge.models.ai import AiSuggestionRequest, AiSuggestionResponse, AiSettings, AiSettingsUpdate
from configforge.services.ai.settings import load_settings, save_settings, mask_key
from configforge.services.ai.factory import create_backend
from configforge.services.ai.orchestrator import build_prompt, parse_response

router = APIRouter()


@router.post("/suggest", response_model=AiSuggestionResponse)
async def suggest(req: AiSuggestionRequest):
    settings = load_settings()
    if not settings.enabled:
        return AiSuggestionResponse(content="AI 未配置，请先在设置中启用", category=req.category)
    try:
        backend = create_backend(settings)
        prompt = build_prompt(req.category, req.context)
        result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
        parsed = parse_response(result)
        return AiSuggestionResponse(content=parsed, category=req.category)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 响应超时，请重试")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg or "invalid" in msg.lower():
            raise HTTPException(status_code=401, detail=f"API Key 无效: {msg}")
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {msg}")


@router.get("/settings")
async def get_settings():
    settings = load_settings()
    data = settings.model_dump()
    data["api_key"] = mask_key(settings.api_key)
    return data


@router.put("/settings")
async def update_settings(body: AiSettingsUpdate):
    existing = load_settings()
    api_key = existing.api_key if body.api_key is None else body.api_key
    dump = body.model_dump(exclude={"api_key"})
    full_settings = AiSettings(api_key=api_key, **dump)
    save_settings(full_settings)
    return {"ok": True}


@router.post("/test")
async def test_connection():
    settings = load_settings()
    if not settings.api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key")
    try:
        backend = create_backend(settings)
        start = time.monotonic()
        await asyncio.wait_for(backend.generate("Hello, respond with just 'ok'."), timeout=15.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"ok": True, "provider": settings.provider.value, "model": settings.model or "default", "latency_ms": latency_ms}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="连接超时")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg:
            raise HTTPException(status_code=401, detail=f"认证失败: {msg}")
        raise HTTPException(status_code=500, detail=f"连接失败: {msg}")
