"""Auto-diagnosis service: automatically diagnose pipeline execution failures."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict

from configforge.services.ai.factory import create_backend
from configforge.services.ai.orchestrator import build_prompt, parse_response
from configforge.services.ai.settings import load_settings

logger = logging.getLogger(__name__)

# ── Diagnosis cache (LRU, max 200 entries, 1h TTL) ──────────────────
_MAX_CACHE_SIZE = 200
_CACHE_TTL_SECONDS = 3600  # 1 hour

_diagnosis_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def _cache_key(yaml_text: str, error_message: str) -> str:
    """Build a deterministic cache key from YAML + error message."""
    payload = f"{yaml_text[:3000]}||{error_message[:2000]}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    """Return cached diagnosis if present and not expired."""
    entry = _diagnosis_cache.get(key)
    if entry is None:
        return None
    ts, diagnosis = entry
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        del _diagnosis_cache[key]
        return None
    # Move to end (most recently used)
    _diagnosis_cache.move_to_end(key)
    return diagnosis


def _cache_put(key: str, diagnosis: dict) -> None:
    """Store diagnosis in cache, evicting LRU entry if at capacity."""
    _diagnosis_cache[key] = (time.monotonic(), diagnosis)
    _diagnosis_cache.move_to_end(key)
    while len(_diagnosis_cache) > _MAX_CACHE_SIZE:
        _diagnosis_cache.popitem(last=False)


async def auto_diagnose(
    yaml_text: str,
    error_message: str,
    scene_name: str = "",
    inputs_summary: list[dict] | None = None,
    processors_summary: list[dict] | None = None,
) -> dict | None:
    """Automatically diagnose a pipeline execution failure using AI.

    Returns a diagnosis dict with cause, suggestions, severity, and step,
    or None if AI is not configured or diagnosis fails.
    """
    try:
        settings = load_settings()
        if not settings.enabled:
            return None

        # Check cache first
        cache_k = _cache_key(yaml_text, error_message)
        cached = _cache_get(cache_k)
        if cached is not None:
            logger.info("Diagnosis cache hit")
            return cached

        context = {
            "yaml": yaml_text[:3000],
            "errorLog": error_message[:2000],
            "scene_name": scene_name,
        }
        if inputs_summary:
            context["inputs"] = json.dumps(inputs_summary, ensure_ascii=False)[:500]
        if processors_summary:
            context["processors"] = json.dumps(processors_summary, ensure_ascii=False)[:500]

        prompt = build_prompt("diagnose", context)

        backend = create_backend(settings)
        try:
            raw = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
        finally:
            await backend.close()

        parsed = parse_response(raw)
        diagnosis = json.loads(parsed)

        # Validate structure
        if not isinstance(diagnosis, dict):
            return None

        # If parse_response wrapped non-JSON output, discard it
        if diagnosis.get("is_json") is False:
            return None

        # Ensure required fields
        diagnosis.setdefault("cause", "未知原因")
        diagnosis.setdefault("suggestions", [])
        diagnosis.setdefault("severity", "warning")
        diagnosis.setdefault("impact", "")

        # Try to infer step number from suggestions or error context
        step = _infer_step(error_message, diagnosis.get("suggestions", []))
        diagnosis["step"] = step

        # Store in cache
        _cache_put(cache_k, diagnosis)

        return diagnosis

    except Exception as exc:
        logger.warning(f"Auto-diagnosis failed: {exc}")
        return None


def _infer_step(error_message: str, suggestions: list) -> int:
    """Infer which wizard step the error relates to."""
    msg_lower = error_message.lower()
    suggestions_text = " ".join(str(s).lower() for s in suggestions)

    # Step 2: input-related errors
    if any(kw in msg_lower for kw in ["file not found", "sheet", "encoding", "delimiter", "input", "输入源"]):
        return 2
    if any(kw in suggestions_text for kw in ["输入源", "文件", "sheet"]):
        return 2

    # Step 3: SQL/processor errors
    if any(kw in msg_lower for kw in ["sql", "syntax", "table", "column", "no such", "query", "processor"]):
        return 3
    if any(kw in suggestions_text for kw in ["sql", "处理器", "查询"]):
        return 3

    # Step 4: output errors
    if any(kw in msg_lower for kw in ["output", "write", "permission", "输出", "连接"]):
        return 4
    if any(kw in suggestions_text for kw in ["输出", "列映射", "目标表"]):
        return 4

    # Default: unknown step
    return 0
