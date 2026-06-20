import json

try:
    import ijson  # type: ignore[import-untyped]

    _HAS_IJSON = True
except ImportError:
    _HAS_IJSON = False


MAX_JSON_ROWS = 50000


def read_json_info(
    file_content: bytes,
    flatten_separator: str = ".",
    max_sample_rows: int = 10,
    max_rows: int = MAX_JSON_ROWS,
) -> dict:
    """Read JSON file content, return columns and sample_rows (same interface as read_excel_info).

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
