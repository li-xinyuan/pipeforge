"""JSON 流式读取器（pipeforge 层）。

限制③C：为 ReaderBackedInputPlugin 提供全量读取接口。
本模块是纯数据工具，不依赖 configforge。
configforge/services/json_reader.py 通过 re-export 复用，保持向后兼容。
"""
import json
from collections.abc import Iterator

try:
    import ijson  # type: ignore[import-untyped]

    _HAS_IJSON = True
except ImportError:
    _HAS_IJSON = False


MAX_JSON_ROWS = 50000


def iter_json_rows(
    file_content: bytes,
    flatten_separator: str = ".",
) -> tuple[list[str], Iterator[tuple]]:
    """全量读取 JSON，返回 (列名列表, 行迭代器)。

    限制③C reader 适配器第一步：为 ReaderBackedInputPlugin 提供全量读取接口。
    与 read_json_info（轻量预览）不同，本函数流式产出所有行，供 pipeline 执行。

    两遍扫描（file_content 已在内存，二次解析成本低）：
    1. 第一遍：收集所有列名（不同行可能有不同键，取并集）
    2. 第二遍：按列名顺序产出每行为 tuple（缺失键 → ""）

    Args:
        file_content: JSON 文件原始字节
        flatten_separator: 嵌套对象拍平分隔符（默认 "."）

    Returns:
        (columns, row_iterator): 列名列表 + 行元组迭代器
    """
    columns = _collect_json_columns(file_content, flatten_separator)
    return columns, _iter_json_rows(file_content, flatten_separator, columns)


def _collect_json_columns(file_content: bytes, flatten_separator: str) -> list[str]:
    """第一遍：收集所有列名（键的并集）。"""
    all_keys: list[str] = []
    seen: set[str] = set()

    for flat in _iter_flat_dicts(file_content, flatten_separator):
        for key in flat:
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    return all_keys


def _iter_json_rows(
    file_content: bytes,
    flatten_separator: str,
    columns: list[str],
) -> Iterator[tuple]:
    """第二遍：按列名顺序产出每行为 tuple。"""
    for flat in _iter_flat_dicts(file_content, flatten_separator):
        yield tuple(str(flat.get(col, "")) if flat.get(col, "") is not None else "" for col in columns)


def _iter_flat_dicts(file_content: bytes, flatten_separator: str) -> Iterator[dict]:
    """流式产出拍平后的 dict（ijson 优先，fallback 全量加载）。"""
    if _HAS_IJSON:
        yield from _iter_flat_dicts_streaming(file_content, flatten_separator)
    else:
        yield from _iter_flat_dicts_fallback(file_content, flatten_separator)


def _iter_flat_dicts_streaming(file_content: bytes, flatten_separator: str) -> Iterator[dict]:
    """ijson 流式产出。

    若顶层不是数组（如单个对象），ijson.items(stream, "item", ...) 不会抛
    JSONError，只是静默产出 0 项。需自行检测并 fallback 到全量加载。
    """
    import io as _io

    stream = _io.BytesIO(file_content)
    yielded = False
    try:
        parser = ijson.items(stream, "item", use_float=True)
        for item in parser:
            if isinstance(item, dict):
                yielded = True
                yield _flatten(item, separator=flatten_separator)
    except ijson.JSONError:
        # 非顶层数组，回退到全量加载
        yield from _iter_flat_dicts_fallback(file_content, flatten_separator)
        return

    # 顶层是单个对象等情况：流式未产出任何项，回退到全量加载
    if not yielded:
        yield from _iter_flat_dicts_fallback(file_content, flatten_separator)


def _iter_flat_dicts_fallback(file_content: bytes, flatten_separator: str) -> Iterator[dict]:
    """无 ijson 时全量加载后产出。"""
    data = json.loads(file_content.decode("utf-8"))
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return
    for item in data:
        if isinstance(item, dict):
            yield _flatten(item, separator=flatten_separator)


def read_json_info(
    file_content: bytes,
    flatten_separator: str = ".",
    max_sample_rows: int = 10,
    max_rows: int = MAX_JSON_ROWS,
) -> dict:
    """Read JSON file content, return columns and sample_rows (preview interface).

    Supports:
    - Array of objects: [{"col1": "val1", ...}, ...]
    - Nested objects: flattened using separator (e.g. "parent.child")

    When ``ijson`` is available, large JSON arrays are parsed in streaming
    fashion so that only the first *max_rows* items are materialised in
    memory.  When ``ijson`` is not installed the function falls back to
    ``json.loads`` which reads the entire document.
    """
    if _HAS_IJSON:
        return _read_json_streaming(file_content, flatten_separator, max_sample_rows, max_rows)

    return _read_json_fallback(file_content, flatten_separator, max_sample_rows, max_rows)


def _read_json_fallback(
    file_content: bytes,
    flatten_separator: str,
    max_sample_rows: int,
    max_rows: int,
) -> dict:
    """Fallback implementation using json.loads (reads entire file)."""
    data = json.loads(file_content.decode("utf-8"))

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or len(data) == 0:
        return {"sheets": [], "columns": [], "sample_rows": []}

    flat_rows = []
    all_keys: list[str] = []

    for i, item in enumerate(data):
        if i >= max_rows:
            break
        if not isinstance(item, dict):
            continue
        flat = _flatten(item, separator=flatten_separator)
        flat_rows.append(flat)
        for key in flat:
            if key not in all_keys:
                all_keys.append(key)

    if not flat_rows:
        return {"sheets": [], "columns": [], "sample_rows": []}

    columns = all_keys
    sample_rows = []
    for row in flat_rows[:max_sample_rows]:
        sample_rows.append([str(row.get(col, "")) for col in columns])

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }


def _read_json_streaming(
    file_content: bytes,
    flatten_separator: str,
    max_sample_rows: int,
    max_rows: int,
) -> dict:
    """Streaming implementation using ijson — only materialises up to *max_rows* items."""
    import io as _io

    flat_rows: list[dict] = []
    all_keys: list[str] = []

    # Try streaming over a top-level array
    stream = _io.BytesIO(file_content)
    try:
        parser = ijson.items(stream, "item", use_float=True)
        for i, item in enumerate(parser):
            if i >= max_rows:
                break
            if not isinstance(item, dict):
                continue
            flat = _flatten(item, separator=flatten_separator)
            flat_rows.append(flat)
            for key in flat:
                if key not in all_keys:
                    all_keys.append(key)
    except ijson.JSONError:
        # Not a top-level array — fall back to full parse
        return _read_json_fallback(file_content, flatten_separator, max_sample_rows, max_rows)

    # If nothing was collected the JSON might be a single object, not an array
    if not flat_rows:
        return _read_json_fallback(file_content, flatten_separator, max_sample_rows, max_rows)

    columns = all_keys
    sample_rows = []
    for row in flat_rows[:max_sample_rows]:
        sample_rows.append([str(row.get(col, "")) for col in columns])

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }


def _flatten(obj: dict, separator: str = ".", prefix: str = "") -> dict:
    """Flatten a nested dict using the given separator."""
    items: dict = {}
    for key, value in obj.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        if isinstance(value, dict):
            items.update(_flatten(value, separator=separator, prefix=new_key))
        elif isinstance(value, list):
            # Convert list to string representation
            items[new_key] = json.dumps(value, ensure_ascii=False) if value else ""
        else:
            items[new_key] = value if value is not None else ""
    return items
