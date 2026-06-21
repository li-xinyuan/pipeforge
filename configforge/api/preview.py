import os
import re
import sqlite3

from fastapi import APIRouter, HTTPException

from configforge.models.wizard import ErrorResponse, PreviewRequest, SqlExecuteRequest, SqlExecuteResponse
from configforge.services.reader_dispatch import infer_file_type, read_file_info
from configforge.utils.paths import get_upload_dir
from configforge.utils.security import safe_identifier, validate_id

router = APIRouter(tags=["数据预览"])
UPLOAD_DIR = get_upload_dir()


def _infer_sql_type(col_name: str, col_index: int, sample_rows: list[list]) -> str:
    """Infer SQLite column type from sample data values."""
    samples = []
    for row in sample_rows:
        if col_index < len(row) and row[col_index] is not None and str(row[col_index]).strip():
            samples.append(str(row[col_index]).strip())
    if not samples:
        return "TEXT"
    # Check if all values are integers
    if all(_is_int(v) for v in samples):
        return "INTEGER"
    # Check if all values are numbers
    if all(_is_number(v) for v in samples):
        return "REAL"
    # Check if all values look like booleans
    if all(v.lower() in ("true", "false", "0", "1", "yes", "no") for v in samples):
        return "BOOLEAN"
    return "TEXT"


def _is_int(v: str) -> bool:
    try:
        int(v)
        return True
    except ValueError:
        return False


def _is_number(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False

_DDL_DML_RE = re.compile(
    r"\b(ALTER|ANALYZE|ATTACH|BEGIN|COMMIT|CREATE|DELETE|DETACH|DROP|INSERT|"
    r"PRAGMA|REINDEX|RELEASE|REPLACE|ROLLBACK|SAVEPOINT|UPDATE|VACUUM)\b",
    re.IGNORECASE,
)


@router.post("/file", summary="预览上传文件", description="预览已上传文件的内容。返回工作表列表、列名和样本行数据。支持 Excel 多工作表选择和行数限制。")
async def preview_file(req: PreviewRequest):
    try:
        validate_id(req.file_id, "file_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file_id format")
    path = os.path.join(UPLOAD_DIR, req.file_id)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="File not found", code="FILE_NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    file_size = os.path.getsize(path)
    info = read_file_info(path, sheet_name=req.sheet, max_rows=req.max_rows)
    result = {
        "sheets": info["sheets"],
        "columns": info["columns"],
        "rows": [
            [str(v) if v else "" for v in row] for row in info["sample_rows"]
        ],
    }
    if file_size > 10 * 1024 * 1024:
        result["warning"] = f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds 10MB. Only preview data is loaded."
    return result


@router.post("/sql", summary="执行预览 SQL", description="在内存 SQLite 数据库中执行 SQL 查询进行数据预览。将上传的文件加载为临时表，仅允许 SELECT 查询，自动添加 LIMIT 限制结果行数。禁止 DDL/DML 语句。")
async def execute_sql(req: SqlExecuteRequest) -> SqlExecuteResponse:
    """Execute a SQL query against uploaded files loaded into an in-memory SQLite database.

    Loads each file from ``table_mapping`` as a table, then runs the query
    with an added LIMIT to avoid returning huge result sets.
    """
    conn = sqlite3.connect(":memory:")
    total_source_rows = 0
    sample_rows_loaded = 0
    try:
        for table_name, file_id in req.table_mapping.items():
            try:
                validate_id(file_id, "file_id")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid file_id format")
            path = os.path.join(UPLOAD_DIR, file_id)
            if not os.path.exists(path):
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error=f"File not found: {file_id}",
                        code="FILE_NOT_FOUND",
                        recoverable=True,
                    ).model_dump(),
                )
            file_type = infer_file_type(file_id)

            info = read_file_info(path, file_type=file_type)

            total_source_rows += info.get("total_rows", 0)
            sample_rows_loaded += len(info.get("sample_rows", []))

            if info["columns"]:
                safe_table = safe_identifier(table_name, "table_name")
                safe_name = f'"{safe_table}"'
                col_defs = ", ".join(
                    f'"{safe_identifier(c, "column_name")}" {_infer_sql_type(c, i, info.get("sample_rows", []))}'
                    for i, c in enumerate(info["columns"])
                )
                conn.execute(f"CREATE TABLE {safe_name} ({col_defs})")
                placeholders = ", ".join("?" for _ in info["columns"])
                for row in info["sample_rows"]:
                    conn.execute(
                        f"INSERT INTO {safe_name} VALUES ({placeholders})",
                        [str(v) if v else "" for v in row],
                    )
        else:
            # No files loaded
            if not req.table_mapping:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error="No table mapping provided",
                        code="NO_TABLES",
                        recoverable=True,
                    ).model_dump(),
                )

        # Data loaded, now enable read-only protection
        conn.execute("PRAGMA query_only=ON")

        # Strip SQL comments before DDL/DML check to prevent bypass via DR/**/OP
        sql_clean = re.sub(r"/\*.*?\*/", "", req.sql, flags=re.DOTALL)
        sql_clean = re.sub(r"--[^\n]*", "", sql_clean)
        if _DDL_DML_RE.search(sql_clean):
            raise HTTPException(
                status_code=400,
                detail="DDL/DML statements are not allowed in preview SQL",
            )

        # Execute with LIMIT (max 5 rows for preview)
        sql = req.sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1].strip()
        # Add LIMIT unless already present
        if "LIMIT" not in sql.upper():
            sql += " LIMIT 5"

        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [[str(v) if v is not None else "" for v in row] for row in cur.fetchall()]
        return SqlExecuteResponse(
            columns=columns,
            rows=rows,
            total_source_rows=total_source_rows,
            sample_rows_loaded=sample_rows_loaded,
            is_sampled=sample_rows_loaded < total_source_rows if total_source_rows > 0 else False,
        )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=f"SQL error: {str(e)}",
                code="SQL_ERROR",
                recoverable=True,
            ).model_dump(),
        )
    finally:
        conn.close()
