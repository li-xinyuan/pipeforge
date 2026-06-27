import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from configforge.middleware.auth import require_role
from configforge.models.ai import (
    AiOrchestrateRequest,
    AiSettings,
    AiSettingsUpdate,
    AiSuggestionRequest,
    AiSuggestionResponse,
)
from configforge.models.user import User
from configforge.services.ai.factory import create_backend
from configforge.services.ai.orchestrator import build_prompt, parse_response
from configforge.services.ai.settings import mask_key
from configforge.storage import get_settings_store
from configforge.utils.rate_limit import RateLimiter

router = APIRouter(tags=["AI 服务"])
logger = logging.getLogger("configforge.ai")

# Persistent rate limiter: 10 requests per 60s window per IP
# Uses file-backed storage so the limit is shared across workers.
_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

_ai_store = get_settings_store('ai')


def _check_rate_limit(client_ip: str) -> None:
    if not _rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")


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


@router.post("/suggest", response_model=AiSuggestionResponse, summary="AI 智能建议", description="根据类别和上下文获取 AI 生成的建议内容。支持 SQL 编写、数据处理、配置优化等场景。每个 IP 限流 10 次/分钟。")
async def suggest(req: AiSuggestionRequest, request: Request, _user: User = Depends(require_role("editor", "admin"))):
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = _ai_store.load_settings()
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


@router.post("/orchestrate", summary="AI 编排多步 Pipeline", description="使用 AI 从自然语言描述规划多步骤 SQL Pipeline。返回包含步骤列表、解释说明和原始响应的编排结果。每个 IP 限流 10 次/分钟。")
async def orchestrate(req: AiOrchestrateRequest, request: Request, _user: User = Depends(require_role("editor", "admin"))):
    """AI plans multi-step SQL pipeline from natural language."""
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = _ai_store.load_settings()
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


@router.post("/translate-checkpoint", summary="AI 翻译检查规则", description="将自然语言描述的数据检查需求翻译为具体的 CheckRule JSON。支持行数检查、空值率检查、唯一性检查、范围检查、枚举检查和自定义 SQL 检查等规则类型。")
async def translate_checkpoint(req: AiSuggestionRequest, request: Request, _user: User = Depends(require_role("editor", "admin"))):
    """将自然语言检查需求翻译为具体的 CheckRule JSON。"""
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = _ai_store.load_settings()
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="AI 未配置，请先在设置中启用")
    backend = None
    try:
        backend = create_backend(settings)
        # Build checkpoint-specific prompt
        available_tables = req.context.get("available_tables", [])
        current_table = req.context.get("current_output_table", "")
        user_input = req.context.get("user_input", "")
        prompt = (
            f"将以下数据检查需求翻译为具体的检查规则 JSON：\n\n"
            f"用户需求：{user_input}\n\n"
            f"上下文：\n"
            f"- 可用表名：{available_tables}\n"
            f"- 当前步骤输出表：{current_table}\n\n"
            f"可用规则类型：\n"
            f'- row_count: 行数检查 {{"type": "row_count", "table": "表名", "min": null, "max": null, "on_failure": "block|warn"}}\n'
            f'- null_rate: 空值率检查 {{"type": "null_rate", "table": "表名", "column": "列名", "max_null_rate": 0.05, "on_failure": "block|warn"}}\n'
            f'- uniqueness: 唯一性检查 {{"type": "uniqueness", "table": "表名", "column": "列名", "on_failure": "block|warn"}}\n'
            f'- value_range: 范围检查 {{"type": "value_range", "table": "表名", "column": "列名", "min_value": null, "max_value": null, "on_failure": "block|warn"}}\n'
            f'- custom_sql: 自定义SQL {{"type": "custom_sql", "sql": "SELECT ...", "result_column": "结果列名", "comparison": ">=", "expected_value": null, "on_failure": "block|warn"}}\n'
            f"  comparison 取值: \"<\" | \"<=\" | \"==\" | \"!=\" | \">\" | \">=\"\n"
            f'- enum_check: 枚举检查 {{"type": "enum_check", "table": "表名", "column": "列名", "allowed_values": ["值1", "值2"], "on_failure": "block|warn"}}\n'
            f"\n"
            f"请返回一个 JSON 对象，包含翻译后的检查规则。例如：\n"
            f'{{"type": "row_count", "table": "result", "min": 100, "on_failure": "block"}}\n\n'
            f"只返回 JSON，不要其他内容。"
        )
        logger.info("AI translate-checkpoint prompt_len=%d model=%s", len(prompt), settings.model)
        start = time.monotonic()
        result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("AI translate-checkpoint latency_ms=%d response_len=%d", latency_ms, len(result))
        parsed_text = parse_response(result)
        try:
            parsed = json.loads(parsed_text)
            parsed.setdefault("on_failure", "block")
            parsed.setdefault("type", "row_count")
            return parsed
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI 返回了无法解析的格式，请重试")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 响应超时，请重试")
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        logger.error("AI translate-checkpoint failed error=%s", msg[:200])
        raise HTTPException(status_code=500, detail="AI 调用失败，请稍后重试")
    finally:
        if backend is not None:
            await backend.close()


@router.get("/settings", summary="获取 AI 设置", description="获取当前 AI 服务的配置信息，包括启用的提供商、模型名称等。API Key 会被脱敏显示。")
async def get_settings(_user: User = Depends(require_role("admin"))):
    settings = _ai_store.load_settings()
    data = settings.model_dump()
    data["api_key"] = mask_key(settings.api_key)
    return data


# ============================================================================
# T-5D-05: AI 辅助增强 — suggest-checkpoint, suggest-mapping, optimize-suggestions
# ============================================================================


def _rule_based_checkpoint_suggestions(columns: list[dict]) -> list[dict]:
    """Rule-based checkpoint suggestions using column metadata heuristics.

    Falls back when AI is not configured. Returns a list of CheckRule dicts.
    """
    suggestions: list[dict] = []
    for col in columns:
        name = (col.get("name") or "").lower()
        col_type = (col.get("type") or "").lower()
        sample_values = col.get("sample_values", [])

        # Email column → suggest regex/uniqueness check
        if "email" in name or "mail" in name:
            suggestions.append({
                "type": "custom_sql",
                "sql": f"SELECT COUNT(*) as cnt FROM {{{{table}}}} WHERE {col.get('name')} NOT LIKE '%@%'",
                "result_column": "cnt",
                "comparison": "==",
                "expected_value": 0,
                "on_failure": "warn",
                "description": f"邮箱格式检查（{col.get('name')}）",
            })

        # Numeric column → suggest range check
        if col_type in ("int", "integer", "float", "double", "decimal", "number"):
            suggestions.append({
                "type": "value_range",
                "table": "{{table}}",
                "column": col.get("name"),
                "min_value": None,
                "max_value": None,
                "on_failure": "warn",
                "description": f"数值范围检查（{col.get('name')}）",
            })

        # ID column → suggest uniqueness check
        if "id" in name or name.endswith("_id") or name == "id":
            suggestions.append({
                "type": "uniqueness",
                "table": "{{table}}",
                "column": col.get("name"),
                "on_failure": "block",
                "description": f"唯一性检查（{col.get('name')}）",
            })

        # Date column → suggest not-null check
        if "date" in name or "time" in name or col_type in ("date", "datetime", "timestamp"):
            suggestions.append({
                "type": "null_rate",
                "table": "{{table}}",
                "column": col.get("name"),
                "max_null_rate": 0.0,
                "on_failure": "warn",
                "description": f"日期非空检查（{col.get('name')}）",
            })

    # Always suggest a row_count check as a baseline
    suggestions.append({
        "type": "row_count",
        "table": "{{table}}",
        "min": 1,
        "max": None,
        "on_failure": "warn",
        "description": "行数检查（确保至少 1 行数据）",
    })

    return suggestions


@router.post("/suggest-checkpoint", summary="AI 推荐检查规则", description="根据数据列特征智能推荐数据检查规则。如检测到 email 列推荐格式检查，检测到数值列推荐范围检查。AI 未配置时使用规则引擎兜底。")
async def suggest_checkpoint(request: Request, _user: User = Depends(require_role("editor", "admin"))):
    """AI 推荐数据检查规则（T-5D-05）。

    请求体示例：
    {
      "columns": [
        {"name": "email", "type": "varchar", "sample_values": ["a@b.com"]},
        {"name": "age", "type": "int", "sample_values": [25, 30]}
      ],
      "table_name": "users"
    }
    """
    _check_rate_limit(request.client.host if request.client else "unknown")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")

    columns = body.get("columns", [])
    table_name = body.get("table_name", "")

    if not isinstance(columns, list) or not columns:
        raise HTTPException(status_code=400, detail="columns 字段必须为非空数组")

    settings = _ai_store.load_settings()

    # If AI is enabled, use AI for richer suggestions
    if settings.enabled:
        backend = None
        try:
            backend = create_backend(settings)
            columns_desc = "\n".join(
                f"- {c.get('name')} ({c.get('type', 'unknown')}): 示例值 {c.get('sample_values', [])[:3]}"
                for c in columns
            )
            prompt = (
                f"根据以下数据列特征，推荐合适的数据检查规则（CheckRule）。\n\n"
                f"表名：{table_name or 'result'}\n"
                f"列信息：\n{columns_desc}\n\n"
                f"可用规则类型：row_count, null_rate, uniqueness, value_range, enum_check, custom_sql\n"
                f"返回 JSON 数组，每个元素是一个检查规则。例如：\n"
                f'[{{"type": "uniqueness", "table": "{table_name or "result"}", "column": "id", "on_failure": "block", "description": "ID 唯一性检查"}}]\n\n'
                f"只返回 JSON 数组，不要其他内容。"
            )
            result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
            parsed_text = parse_response(result)
            try:
                suggestions = json.loads(parsed_text)
                if isinstance(suggestions, list):
                    # Fill in table_name if missing
                    for s in suggestions:
                        if isinstance(s, dict) and "table" in s and s["table"] in ("{{table}}", ""):
                            s["table"] = table_name or "result"
                    return {"suggestions": suggestions, "source": "ai"}
            except json.JSONDecodeError:
                logger.warning("AI suggest-checkpoint returned non-JSON, falling back to rules")
        except asyncio.TimeoutError:
            logger.warning("AI suggest-checkpoint timeout, falling back to rules")
        except Exception as e:
            logger.warning("AI suggest-checkpoint failed: %s, falling back to rules", str(e)[:200])
        finally:
            if backend is not None:
                await backend.close()

    # Fallback to rule-based suggestions
    suggestions = _rule_based_checkpoint_suggestions(columns)
    # Replace {{table}} placeholder with actual table name
    for s in suggestions:
        if isinstance(s, dict) and "table" in s and s["table"] == "{{table}}":
            s["table"] = table_name or "result"
        if isinstance(s, dict) and "sql" in s and "{{table}}" in s["sql"]:
            s["sql"] = s["sql"].replace("{{table}}", table_name or "result")
    return {"suggestions": suggestions, "source": "rules"}


def _rule_based_mapping_suggestions(source_columns: list[str], target_columns: list[str]) -> list[dict]:
    """Rule-based column mapping using name matching heuristics.

    Returns list of {source, target, confidence, reason} dicts.
    """
    # Common synonyms/abbreviations (CN-EN, abbreviations)
    SYNONYMS = {
        "name": ["名称", "名字", "姓名", "nm"],
        "id": ["编号", "标识", "identifier"],
        "email": ["邮箱", "电子邮件", "mail", "e-mail"],
        "phone": ["电话", "手机", "mobile", "tel", "telephone"],
        "address": ["地址", "addr"],
        "age": ["年龄", "岁数"],
        "gender": ["性别", "sex"],
        "date": ["日期", "时间", "time", "created_at", "updated_at"],
        "amount": ["金额", "数量", "money", "price", "total"],
        "status": ["状态", "state"],
        "type": ["类型", "category", "kind"],
        "city": ["城市", "town"],
        "country": ["国家", "nation"],
        "company": ["公司", "企业", "org", "organization"],
        "description": ["描述", "说明", "desc", "remark", "备注"],
    }

    # Build reverse lookup: synonym → canonical
    synonym_to_canonical = {}
    for canonical, syns in SYNONYMS.items():
        for syn in syns:
            synonym_to_canonical[syn.lower()] = canonical
        synonym_to_canonical[canonical] = canonical

    def _normalize(s: str) -> str:
        """Normalize column name: lowercase, remove underscores/spacing."""
        return s.lower().replace("_", "").replace("-", "").replace(" ", "").strip()

    suggestions: list[dict] = []
    used_targets: set[str] = set()

    # First pass: exact matches and synonym matches
    for src in source_columns:
        src_norm = _normalize(src)
        src_canonical = synonym_to_canonical.get(src_norm, src_norm)

        best_target = None
        best_confidence = 0.0
        best_reason = ""

        for tgt in target_columns:
            if tgt in used_targets:
                continue
            tgt_norm = _normalize(tgt)
            tgt_canonical = synonym_to_canonical.get(tgt_norm, tgt_norm)

            if src_norm == tgt_norm:
                best_target = tgt
                best_confidence = 1.0
                best_reason = "名称完全匹配"
                break
            elif src_canonical == tgt_canonical and (
                src_canonical != src_norm or tgt_canonical != tgt_norm
            ):
                # At least one side is a non-canonical synonym → synonym match
                best_target = tgt
                best_confidence = 0.9
                best_reason = "同义词匹配"
                break
            elif src_canonical == tgt_canonical:
                best_target = tgt
                best_confidence = 0.85
                best_reason = "规范化后匹配"

        if best_target:
            suggestions.append({
                "source": src,
                "target": best_target,
                "confidence": best_confidence,
                "reason": best_reason,
            })
            used_targets.add(best_target)

    # Second pass: fuzzy substring matching for unmatched sources
    for src in source_columns:
        if any(s["source"] == src for s in suggestions):
            continue
        src_norm = _normalize(src)

        best_target = None
        best_confidence = 0.0
        for tgt in target_columns:
            if tgt in used_targets:
                continue
            tgt_norm = _normalize(tgt)
            # Substring match
            if src_norm and tgt_norm and (src_norm in tgt_norm or tgt_norm in src_norm):
                confidence = 0.6
                if confidence > best_confidence:
                    best_target = tgt
                    best_confidence = confidence

        if best_target:
            suggestions.append({
                "source": src,
                "target": best_target,
                "confidence": best_confidence,
                "reason": "子串匹配",
            })
            used_targets.add(best_target)

    return suggestions


@router.post("/suggest-mapping", summary="AI 智能列映射", description="根据源列和目标列名称智能匹配，支持同义词、缩写、中英文对照。AI 未配置时使用规则引擎兜底。")
async def suggest_mapping(request: Request, _user: User = Depends(require_role("editor", "admin"))):
    """AI 智能列映射匹配（T-5D-05）。

    请求体示例：
    {
      "source_columns": ["user_name", "email_addr", "phone_number"],
      "target_columns": ["name", "email", "phone"]
    }
    """
    _check_rate_limit(request.client.host if request.client else "unknown")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")

    source_columns = body.get("source_columns", [])
    target_columns = body.get("target_columns", [])

    if not isinstance(source_columns, list) or not source_columns:
        raise HTTPException(status_code=400, detail="source_columns 必须为非空数组")
    if not isinstance(target_columns, list) or not target_columns:
        raise HTTPException(status_code=400, detail="target_columns 必须为非空数组")

    settings = _ai_store.load_settings()

    # If AI is enabled, use AI for smarter matching
    if settings.enabled:
        backend = None
        try:
            backend = create_backend(settings)
            prompt = (
                f"将以下源列与目标列进行智能匹配，考虑同义词、缩写、中英文对照。\n\n"
                f"源列：{json.dumps(source_columns, ensure_ascii=False)}\n"
                f"目标列：{json.dumps(target_columns, ensure_ascii=False)}\n\n"
                f"返回 JSON 数组，每个元素包含 source, target, confidence (0-1), reason。例如：\n"
                f'[{{"source": "user_name", "target": "name", "confidence": 0.95, "reason": "同义词匹配"}}]\n\n'
                f"只返回 JSON 数组，不要其他内容。"
            )
            result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
            parsed_text = parse_response(result)
            try:
                mappings = json.loads(parsed_text)
                if isinstance(mappings, list):
                    return {"mappings": mappings, "source": "ai"}
            except json.JSONDecodeError:
                logger.warning("AI suggest-mapping returned non-JSON, falling back to rules")
        except asyncio.TimeoutError:
            logger.warning("AI suggest-mapping timeout, falling back to rules")
        except Exception as e:
            logger.warning("AI suggest-mapping failed: %s, falling back to rules", str(e)[:200])
        finally:
            if backend is not None:
                await backend.close()

    # Fallback to rule-based matching
    mappings = _rule_based_mapping_suggestions(source_columns, target_columns)
    return {"mappings": mappings, "source": "rules"}


@router.post("/optimize-suggestions", summary="AI 配置优化建议", description="分析 Pipeline 配置后给出优化建议，如建议添加去重步骤、建议添加数据检查点等。AI 未配置时使用规则引擎兜底。")
async def optimize_suggestions(request: Request, _user: User = Depends(require_role("editor", "admin"))):
    """AI 配置优化建议（T-5D-05）。

    请求体示例：
    {
      "state": { ... WizardState ... }
    }
    """
    _check_rate_limit(request.client.host if request.client else "unknown")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")

    state = body.get("state", {})
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="state 必须为对象")

    settings = _ai_store.load_settings()

    # If AI is enabled, use AI for analysis
    if settings.enabled:
        backend = None
        try:
            backend = create_backend(settings)
            # Serialize state summary (avoid sending too much data)
            scene = state.get("scene", {})
            inputs = state.get("inputs", [])
            processors = state.get("processors", [])
            output = state.get("output", {})

            state_summary = {
                "scene_name": scene.get("name", ""),
                "input_count": len(inputs),
                "input_types": [i.get("plugin", "") for i in inputs],
                "processor_count": len(processors),
                "processor_types": [p.get("plugin", "") for p in processors],
                "output_type": output.get("plugin", "") if output else "",
                "has_checkpoints": any(p.get("plugin") == "check" for p in processors),
                "has_dedup": any(p.get("plugin") == "dedup" for p in processors),
            }

            prompt = (
                f"分析以下 Pipeline 配置，给出优化建议。\n\n"
                f"配置摘要：{json.dumps(state_summary, ensure_ascii=False, indent=2)}\n\n"
                f"请从以下方面分析：\n"
                f"1. 是否缺少数据检查点\n"
                f"2. 是否缺少去重步骤\n"
                f"3. 是否缺少错误处理\n"
                f"4. 性能优化建议\n"
                f"5. 数据质量保障建议\n\n"
                f"返回 JSON 数组，每个元素包含 category, suggestion, priority (high/medium/low)。例如：\n"
                f'[{{"category": "数据质量", "suggestion": "建议添加行数检查点", "priority": "medium"}}]\n\n'
                f"只返回 JSON 数组，不要其他内容。"
            )
            result = await asyncio.wait_for(backend.generate(prompt), timeout=30.0)
            parsed_text = parse_response(result)
            try:
                suggestions = json.loads(parsed_text)
                if isinstance(suggestions, list):
                    return {"suggestions": suggestions, "source": "ai"}
            except json.JSONDecodeError:
                logger.warning("AI optimize-suggestions returned non-JSON, falling back to rules")
        except asyncio.TimeoutError:
            logger.warning("AI optimize-suggestions timeout, falling back to rules")
        except Exception as e:
            logger.warning("AI optimize-suggestions failed: %s, falling back to rules", str(e)[:200])
        finally:
            if backend is not None:
                await backend.close()

    # Fallback: rule-based optimization suggestions
    suggestions: list[dict] = []
    processors = state.get("processors", [])
    has_checkpoints = any(p.get("plugin") == "check" for p in processors)
    has_dedup = any(p.get("plugin") == "dedup" for p in processors)

    if not has_checkpoints:
        suggestions.append({
            "category": "数据质量",
            "suggestion": "建议添加数据检查点（CheckPoint），在关键步骤后验证数据完整性",
            "priority": "high",
        })

    if not has_dedup:
        suggestions.append({
            "category": "数据质量",
            "suggestion": "建议添加去重步骤，避免数据重复导致分析结果偏差",
            "priority": "medium",
        })

    if len(processors) == 0:
        suggestions.append({
            "category": "数据处理",
            "suggestion": "当前配置没有数据处理步骤，建议添加必要的转换或过滤处理器",
            "priority": "medium",
        })

    if len(processors) > 5:
        suggestions.append({
            "category": "性能优化",
            "suggestion": "处理步骤较多，建议考虑合并相似步骤或拆分为多个 Pipeline",
            "priority": "low",
        })

    if not suggestions:
        suggestions.append({
            "category": "总体评价",
            "suggestion": "配置结构合理，暂无关键优化建议",
            "priority": "low",
        })

    return {"suggestions": suggestions, "source": "rules"}


@router.put("/settings", summary="更新 AI 设置", description="更新 AI 服务配置，包括提供商、API Key、模型名称等。支持部分更新，未提供的字段保持不变。")
async def update_settings(body: AiSettingsUpdate, _user: User = Depends(require_role("admin"))):
    existing = _ai_store.load_settings()
    api_key = existing.api_key if body.api_key is None else body.api_key
    dump = body.model_dump(exclude={"api_key"})
    full_settings = AiSettings(api_key=api_key, **dump)
    _ai_store.save_settings(full_settings)
    return {"ok": True}


@router.post("/test", summary="测试 AI 连接", description="测试 AI 服务的连接是否正常。发送简单请求验证 API Key 有效性和网络连通性，返回提供商、模型和延迟信息。")
async def test_connection(_user: User = Depends(require_role("admin"))):
    settings = _ai_store.load_settings()
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
