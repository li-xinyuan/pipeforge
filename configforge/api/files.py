import os
import time
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from configforge.models.wizard import ErrorResponse, FileUploadResponse
from configforge.utils.paths import get_log_dir, get_upload_dir

router = APIRouter(tags=["文件管理"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json", ".xml", ".parquet"}
MAX_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_DIR = get_upload_dir()
MAX_FILE_AGE_SECONDS = 24 * 60 * 60

os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_old_files() -> int:
    now = time.time()
    removed = 0
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if not os.path.isfile(path):
            continue
        if now - os.path.getmtime(path) > MAX_FILE_AGE_SECONDS:
            os.remove(path)
            removed += 1
    return removed


cleanup_old_files()


LOG_DIR = get_log_dir()
MAX_LOG_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def cleanup_old_logs() -> int:
    if not os.path.isdir(LOG_DIR):
        return 0
    now = time.time()
    removed = 0
    for name in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, name)
        if not os.path.isfile(path):
            continue
        if now - os.path.getmtime(path) > MAX_LOG_AGE_SECONDS:
            os.remove(path)
            removed += 1
    return removed


cleanup_old_logs()


@router.post("/upload", response_model=FileUploadResponse, summary="上传文件", description="上传数据文件用于 Pipeline 输入。支持 xlsx、xls、csv、json、xml、parquet 格式，文件大小限制为 50MB。上传后会自动验证文件格式与内容是否匹配。")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="No file provided",
                code="VALIDATION_ERROR",
                recoverable=True,
            ).model_dump(),
        )
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error=f"Unsupported format '{ext}'",
                code="FILE_FORMAT_UNSUPPORTED",
                recoverable=True,
            ).model_dump(),
        )

    file_id = uuid.uuid4().hex + ext
    path = os.path.join(UPLOAD_DIR, file_id)
    chunk_size = 1024 * 1024  # 1MB chunks
    total_size = 0
    first_chunk = None

    try:
        with open(path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=ErrorResponse(
                            error="File exceeds 50MB limit",
                            code="FILE_TOO_LARGE",
                            recoverable=True,
                        ).model_dump(),
                    )
                if first_chunk is None:
                    first_chunk = chunk
                    # Validate file content matches declared type
                    if ext in (".xlsx", ".xls") and chunk[:4] != b"PK\x03\x04":
                        raise HTTPException(
                            status_code=422,
                            detail=ErrorResponse(
                                error="File content does not match xlsx format",
                                code="FILE_FORMAT_UNSUPPORTED",
                                recoverable=True,
                            ).model_dump(),
                        )
                    if ext == ".csv":
                        try:
                            chunk.decode("utf-8")
                        except UnicodeDecodeError:
                            raise HTTPException(
                                status_code=422,
                                detail=ErrorResponse(
                                    error="CSV file is not valid UTF-8 text",
                                    code="FILE_FORMAT_UNSUPPORTED",
                                    recoverable=True,
                                ).model_dump(),
                            )
                    if ext == ".json":
                        try:
                            chunk.decode("utf-8")
                        except UnicodeDecodeError:
                            raise HTTPException(
                                status_code=422,
                                detail=ErrorResponse(
                                    error="JSON file is not valid UTF-8 text",
                                    code="FILE_FORMAT_UNSUPPORTED",
                                    recoverable=True,
                                ).model_dump(),
                            )
                    if ext == ".xml":
                        try:
                            chunk.decode("utf-8")
                        except UnicodeDecodeError:
                            raise HTTPException(
                                status_code=422,
                                detail=ErrorResponse(
                                    error="XML file is not valid UTF-8 text",
                                    code="FILE_FORMAT_UNSUPPORTED",
                                    recoverable=True,
                                ).model_dump(),
                            )
                f.write(chunk)
    except HTTPException:
        # Clean up partial file on validation error
        if os.path.exists(path):
            os.remove(path)
        raise

    file_type = "csv" if ext == ".csv" else "json" if ext == ".json" else "xml" if ext == ".xml" else "parquet" if ext == ".parquet" else "excel"
    import json
    meta_path = os.path.join(UPLOAD_DIR, file_id + ".meta.json")
    with open(meta_path, "w") as f:
        json.dump({"original_name": file.filename, "type": file_type}, f)

    return {"file_id": file_id, "original_name": file.filename}
