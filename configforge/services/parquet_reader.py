"""Parquet reader（configforge 兼容层）。

限制③C：核心读取逻辑已迁移到 pipeforge.readers.parquet。
本模块 re-export 所有公共接口，保持向后兼容。
"""
from pipeforge.readers.parquet import (
    iter_parquet_rows,
    read_parquet_info,
)

__all__ = ["read_parquet_info", "iter_parquet_rows"]
