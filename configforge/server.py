import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from configforge.api.preview import router as preview_router
from configforge.api.files import router as files_router
from configforge.api.ai import router as ai_router
from configforge.api.wizard import router as wizard_router
from configforge.api.configs import router as configs_router
from configforge.api.connections import router as connections_router
from configforge.models.wizard import ErrorResponse

app = FastAPI(title="ConfigForge", version="0.1.0")

# URL-encoded path traversal patterns — checked against raw_path (URL-encoded) before Starlette normalizes
_RAW_TRAVERSAL_RE = re.compile(r"(%[2eE][%2eE]|%[2fF]|%[5cC]|%00)", re.IGNORECASE)


@app.middleware("http")
async def block_encoded_traversal(request: Request, call_next):
    raw = request.scope.get("raw_path", request.url.path.encode()).decode("latin-1", errors="replace")
    if _RAW_TRAVERSAL_RE.search(raw) or ".." in raw:
        return JSONResponse(
            status_code=400,
            content={"error": "Path traversal detected", "code": "PATH_TRAVERSAL", "recoverable": False},
        )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(detail), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


app.include_router(preview_router, prefix="/api/preview")
app.include_router(files_router, prefix="/api/files")
app.include_router(ai_router, prefix="/api/ai")
app.include_router(wizard_router, prefix="/api/wizard")
app.include_router(configs_router, prefix="/api/configs")
app.include_router(connections_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

_static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(_static_dir, full_path)
        real = os.path.realpath(file_path)
        if not real.startswith(os.path.realpath(_static_dir) + os.sep):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})
        if full_path and os.path.isfile(real):
            return FileResponse(real)
        index_path = os.path.join(_static_dir, "index.html")
        return FileResponse(index_path)
