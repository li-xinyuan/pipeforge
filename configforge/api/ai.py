import asyncio
import json
import logging
import time
from fastapi import APIRouter, HTTPException, Request
from configforge.models.ai import AiOrchestrateRequest, AiSuggestionRequest, AiSuggestionResponse, AiSettings, AiSettingsUpdate
from configforge.services.ai.settings import load_settings, save_settings, mask_key
from configforge.services.ai.factory import create_backend
from configforge.services.ai.orchestrator import build_prompt, parse_response

router = APIRouter()
logger = logging.getLogger("configforge.ai")

# Simple in-memory rate limiter: 10 requests per 60s window per IP
_rate_window_sec = 60
_rate_max_requests = 10
_rate_store: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    if client_ip not in _rate_store:
        _rate_store[client_ip] = []
    # Purge expired entries
    window_start = now - _rate_window_sec
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > window_start]
    if len(_rate_store[client_ip]) >= _rate_max_requests:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")
    _rate_store[client_ip].append(now)


def _sanitize_error(msg: str) -> str:
    """Redact potential key/credential fragments from error messages before forwarding to client."""
    import re
    # Redact API key-like patterns (sk-..., key:..., etc.)
    msg = re.sub(r'sk-[A-Za-z0-9_\-]{10,}', '[REDACTED]', msg)
    msg = re.sub(r'Bearer\s+[A-Za-z0-9_\-.]{10,}', 'Bearer [REDACTED]', msg)
    msg = re.sub(r'api[_-]?key[=:]\s*["\']?\w+', 'api_key=[REDACTED]', msg, flags=re.IGNORECASE)
    # Truncate to prevent error message abuse
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


@router.post("/suggest", response_model=AiSuggestionResponse)
async def suggest(req: AiSuggestionRequest, request: Request):
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = load_settings()
    if not settings.enabled:
        return AiSuggestionResponse(content="AI 未配置，请先在设置中启用", category=req.category)
    backend = None
    try:
        backend = create_backend(settings)
        prompt = build_prompt(req.category, req.context)
        logger.info("AI suggest request category=%s prompt_len=%d model=%s provider=%s",
                     req.category, len(prompt), settings.model, settings.provider.value)
        start = time.monotonic()
        result = await asyncio.wait_for(backend.generate(prompt), timeout=90.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("AI suggest response category=%s latency_ms=%d response_len=%d",
                     req.category, latency_ms, len(result))
        parsed = parse_response(result)
        return AiSuggestionResponse(content=parsed, category=req.category)
    except asyncio.TimeoutError:
        logger.warning("AI suggest timeout category=%s model=%s", req.category, settings.model)
        raise HTTPException(status_code=503, detail="AI 响应超时，请重试")
    except Exception as e:
        msg = str(e)
        logger.error("AI suggest failed category=%s error=%s", req.category, msg[:200])
        if "401" in msg or "403" in msg or "invalid" in msg.lower():
            raise HTTPException(status_code=401, detail="API Key 无效，请检查设置")
        raise HTTPException(status_code=500, detail="AI 调用失败，请稍后重试")
    finally:
        if backend is not None:
            await backend.close()


@router.post("/orchestrate")
async def orchestrate(req: AiOrchestrateRequest, request: Request):
    """AI plans multi-step SQL pipeline from natural language."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = load_settings()
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="AI 未配置，请先在设置中启用")
    backend = None
    try:
        backend = create_backend(settings)
        prompt = build_prompt("orchestrate", req.context)
        logger.info("AI orchestrate prompt_len=%d model=%s", len(prompt), settings.model)
        start = time.monotonic()
        result = await asyncio.wait_for(backend.generate(prompt), timeout=90.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("AI orchestrate latency_ms=%d response_len=%d", latency_ms, len(result))

        parsed_text = parse_response(result)
        try:
            parsed = json.loads(parsed_text)
        except json.JSONDecodeError:
            return {"steps": [], "explanation": "", "raw": result, "parse_error": True}

        # parse_response wraps non-JSON as {"raw": ..., "is_json": false}
        if isinstance(parsed, dict) and parsed.get("is_json") is False:
            return {"steps": [], "explanation": "", "raw": parsed.get("raw", result), "parse_error": True}

        return {
            "steps": parsed.get("steps") or [],
            "explanation": parsed.get("explanation", ""),
            "raw": result,
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 响应超时，请稍后重试")
    except Exception as e:
        msg = str(e)
        logger.error("AI orchestrate failed error=%s", msg[:200])
        raise HTTPException(status_code=500, detail="AI 调用失败，请稍后重试")
    finally:
        if backend is not None:
            await backend.close()


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
    backend = None
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
        logger.error("AI connection test failed error=%s", msg[:200])
        if "401" in msg or "403" in msg:
            raise HTTPException(status_code=401, detail="认证失败，请检查 API Key")
        raise HTTPException(status_code=500, detail="连接失败，请检查网络和设置")
    finally:
        if backend is not None:
            await backend.close()
