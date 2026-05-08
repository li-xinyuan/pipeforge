import os
from fastapi import APIRouter, HTTPException
from configforge.models.wizard import ErrorResponse, PreviewRequest
from configforge.services.excel_reader import read_excel_info

router = APIRouter()
UPLOAD_DIR = "tmp/uploads"


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
        info = read_excel_info(f, sheet_name=req.sheet)
    return {
        "sheets": info["sheets"],
        "columns": info["columns"],
        "rows": [
            [str(v) if v else "" for v in row] for row in info["sample_rows"]
        ],
    }
