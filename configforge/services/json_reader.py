import json


MAX_JSON_ROWS = 50000


def read_json_info(file_content: bytes, flatten_separator: str = ".", max_sample_rows: int = 10) -> dict:
    """Read JSON file content, return columns and sample_rows (same interface as read_excel_info).

    Supports:
    - Array of objects: [{"col1": "val1", ...}, ...]
    - Nested objects: flattened using separator (e.g. "parent.child")
    """
    data = json.loads(file_content.decode("utf-8"))

    if isinstance(data, dict):
        # Single object -> wrap in array
        data = [data]

    if not isinstance(data, list) or len(data) == 0:
        return {"sheets": [], "columns": [], "sample_rows": []}

    # Flatten nested objects and collect all keys
    flat_rows = []
    all_keys: list[str] = []

    for i, item in enumerate(data):
        if i >= MAX_JSON_ROWS:
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
