import json
import os
from fastapi import APIRouter, HTTPException
from configforge.models.wizard import ErrorResponse, PreviewRequest
from configforge.services.excel_reader import read_excel_info
from configforge.services.csv_reader import read_csv_info

router = APIRouter()
UPLOAD_DIR = "tmp/uploads"


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
