import io
import json
import os
import re
import sqlite3
from fastapi import APIRouter, HTTPException
from configforge.models.wizard import ErrorResponse, PreviewRequest, SqlExecuteRequest, SqlExecuteResponse
from configforge.services.excel_reader import read_excel_info
from configforge.services.csv_reader import read_csv_info
from configforge.utils.security import validate_id

router = APIRouter()
UPLOAD_DIR = os.environ.get("CONFIGFORGE_UPLOAD_DIR", "tmp/uploads")

_DDL_DML_RE = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|ATTACH|DETACH|REINDEX|VACUUM)\b",
    re.IGNORECASE,
)


def _get_file_type(file_id: str) -> str:
    """Determine file type from upload metadata, fall back to extension."""
    meta_path = os.path.join(UPLOAD_DIR, file_id + ".meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
        return meta.get("type", "excel")
    return "csv" if os.path.splitext(file_id)[1].lower() == ".csv" else "excel"


@router.post("/file")
async def preview_file(req: PreviewRequest):
    try:
        validate_id(req.file_id, "file_id")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    path = os.path.join(UPLOAD_DIR, req.file_id)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="File not found", code="FILE_NOT_FOUND", recoverable=True
            ).model_dump(),
        )
    with open(path, "rb") as f:
        content = f.read()
    file_type = _get_file_type(req.file_id)
    if file_type == "csv":
        info = read_csv_info(content)
    else:
        import io
        info = read_excel_info(io.BytesIO(content), sheet_name=req.sheet)
    return {
        "sheets": info["sheets"],
        "columns": info["columns"],
        "rows": [
            [str(v) if v else "" for v in row] for row in info["sample_rows"]
        ],
    }


@router.post("/sql")
async def execute_sql(req: SqlExecuteRequest) -> SqlExecuteResponse:
    """Execute a SQL query against uploaded files loaded into an in-memory SQLite database.

    Loads each file from ``table_mapping`` as a table, then runs the query
    with an added LIMIT to avoid returning huge result sets.
    """
    conn = sqlite3.connect(":memory:")
    try:
        for table_name, file_id in req.table_mapping.items():
            try:
                validate_id(file_id, "file_id")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
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
            file_type = _get_file_type(file_id)
            with open(path, "rb") as f:
                content = f.read()

            if file_type == "csv":
                info = read_csv_info(content)
            else:
                info = read_excel_info(io.BytesIO(content))

            if info["columns"]:
                safe_name = f'"{table_name}"'
                col_defs = ", ".join(f'"{c}" TEXT' for c in info["columns"])
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

        # Block DDL/DML keywords
        if _DDL_DML_RE.search(req.sql):
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
        return SqlExecuteResponse(columns=columns, rows=rows)
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
