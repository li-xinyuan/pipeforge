"""XML reader（configforge 兼容层）。

限制③C：核心读取逻辑已迁移到 pipeforge.readers.xml。
本模块 re-export 所有公共接口，保持向后兼容。
"""
from pipeforge.readers.xml import (
    MAX_XML_ROWS,
    _element_to_dict,
    _find_row_elements,
    iter_xml_rows,
    read_xml_info,
)

__all__ = [
    "read_xml_info",
    "iter_xml_rows",
    "MAX_XML_ROWS",
    "_element_to_dict",
    "_find_row_elements",
]
