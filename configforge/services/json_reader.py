"""JSON reader（configforge 兼容层）。

限制③C：核心读取逻辑已迁移到 pipeforge.readers.json（避免 pipeforge→configforge 循环依赖）。
本模块 re-export 所有公共接口，保持 configforge.services.json_reader 的向后兼容。
"""
from pipeforge.readers.json import (
    MAX_JSON_ROWS,
    _HAS_IJSON,
    _flatten,
    iter_json_rows,
    read_json_info,
)

__all__ = ["read_json_info", "iter_json_rows", "MAX_JSON_ROWS", "_HAS_IJSON", "_flatten"]
