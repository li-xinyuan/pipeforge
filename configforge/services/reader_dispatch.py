"""Unified file reader dispatch.

Eliminates duplicated if/elif chains for file-type dispatch across
preview.py and pipeline.py (4 occurrences total).
"""

import json
import os

from configforge.services.csv_reader import read_csv_info
from configforge.services.excel_reader import read_excel_info
from configforge.services.json_reader import read_json_info
from configforge.services.parquet_reader import read_parquet_info
from configforge.services.xml_reader import read_xml_info
from configforge.utils.paths import get_upload_dir

SUPPORTED_TYPES = ("csv", "json", "xml", "parquet", "excel")


def read_file_info(
    file_path: str,
    file_type: str | None = None,
    *,
    content: bytes | None = None,
    sheet_name: str | None = None,
    max_rows: int | None = None,
) -> dict:
    """Unified file reader dispatch entry point.

    Args:
        file_path: Absolute path to the uploaded file.
        file_type: File type identifier. If None, auto-inferred from metadata/extension.
        content: Optional raw file bytes. If None, reader reads from file_path directly.
        sheet_name: Excel-specific sheet name.
        max_rows: Optional maximum number of rows to read. If None, reader defaults apply.

    Returns:
        dict with "sheets", "columns", "sample_rows", "total_rows" etc.
    """
    if file_type is None:
        file_type = infer_file_type(os.path.basename(file_path))

    if file_type == "csv":
        kwargs: dict = {}
        if max_rows is not None:
            kwargs["max_sample_rows"] = max_rows
        return read_csv_info(file_path, **kwargs)
    elif file_type == "json":
        if content is None:
            with open(file_path, "rb") as f:
                content = f.read()
        kwargs = {}
        if max_rows is not None:
            kwargs["max_rows"] = max_rows
        return read_json_info(content, **kwargs)
    elif file_type == "xml":
        if content is None:
            with open(file_path, "rb") as f:
                content = f.read()
        kwargs = {}
        if max_rows is not None:
            kwargs["max_rows"] = max_rows
        return read_xml_info(content, **kwargs)
    elif file_type == "parquet":
        return read_parquet_info(file_path)
    else:  # excel (default)
        with open(file_path, "rb") as f:
            return read_excel_info(f, sheet_name=sheet_name)


def infer_file_type(file_id: str) -> str:
    """Infer file type from upload metadata (.meta.json) or file extension.

    This is the single source of truth for file type inference,
    replacing the duplicated _get_file_type() in preview.py.
    """
    upload_dir = get_upload_dir()
    meta_path = os.path.join(upload_dir, file_id + ".meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        return meta.get("type", "excel")

    ext = os.path.splitext(file_id)[1].lower()
    ext_map = {".csv": "csv", ".json": "json", ".xml": "xml", ".parquet": "parquet"}
    return ext_map.get(ext, "excel")
