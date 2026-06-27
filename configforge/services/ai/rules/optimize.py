"""规则引擎：配置优化建议。

从 api/ai.py 抽取，当 AI 未配置时基于 Pipeline 配置结构启发式给出优化建议。
"""


def optimize_suggestions(state: dict) -> list[dict]:
    """Rule-based optimization suggestions from a WizardState dict.

    Returns a list of {category, suggestion, priority} dicts.
    """
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

    return suggestions
