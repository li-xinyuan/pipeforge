"""AI 规则引擎：AI 未配置时的启发式兜底建议。

从 api/ai.py 抽取，使路由层只关注 HTTP 编排，规则逻辑可独立测试与复用。
"""

from configforge.services.ai.rules.checkpoint import checkpoint_suggestions
from configforge.services.ai.rules.mapping import mapping_suggestions
from configforge.services.ai.rules.optimize import optimize_suggestions

__all__ = [
    "checkpoint_suggestions",
    "mapping_suggestions",
    "optimize_suggestions",
]
