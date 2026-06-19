import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from configforge.api.preview import router as preview_router
from configforge.api.files import router as files_router, cleanup_old_files, cleanup_old_logs
from configforge.api.ai import router as ai_router
from configforge.api.wizard import router as wizard_router
from configforge.api.configs import router as configs_router
from configforge.api.connections import router as connections_router
from configforge.api.executions import router as exec_router, _cleanup_old_outputs
from configforge.api.schedules import router as schedules_router
from configforge.api.notifications import router as notifications_router
from configforge.api.templates import router as templates_router
from configforge.models.wizard import ErrorResponse
from configforge.scheduler import start_scheduler, shutdown_scheduler
from configforge.middleware.auth import AuthMiddleware
from configforge.services.template_store import ensure_builtin_templates


def _get_version() -> str:
    """Read version from pyproject.toml (works in dev mode)."""
    try:
        from importlib.metadata import version as pkg_version
        return pkg_version("pipeforge")
    except Exception:
        pass
    # Fallback: read pyproject.toml directly
    try:
        import tomllib
        pyproject_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


_CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour

_logger = logging.getLogger("configforge")


async def _periodic_cleanup():
    """Background task: periodically clean old temp files, logs, and outputs."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        try:
            cleanup_old_files()
            cleanup_old_logs()
            _cleanup_old_outputs()
        except Exception:
            pass  # Don't crash the background task


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    ensure_builtin_templates()
    if not os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"):
        _logger.warning(
            "CONFIGFORGE_ENCRYPTION_KEY not set. Auto-generated encryption key "
            "will be lost on container restart. Set this variable in production "
            "to prevent data loss."
        )
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    yield
    cleanup_task.cancel()
    shutdown_scheduler()


app = FastAPI(title="ConfigForge", version=_get_version(), lifespan=lifespan)

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


_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

# Development fallback: allow localhost if no origins configured
if not _cors_origins:
    _cors_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# API Key authentication (disabled when CONFIGFORGE_API_KEY is not set)
app.add_middleware(AuthMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict):
        if "code" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        # Preserve structured error info (e.g., checkpoint checks)
        return JSONResponse(status_code=exc.status_code, content={"error": str(detail), **detail})
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(detail), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError (e.g., from validate_id) as 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=str(exc), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


app.include_router(preview_router, prefix="/api/preview")
app.include_router(files_router, prefix="/api/files")
app.include_router(ai_router, prefix="/api/ai")
app.include_router(wizard_router, prefix="/api/wizard")
app.include_router(configs_router, prefix="/api/configs")
app.include_router(connections_router, prefix="/api")
app.include_router(exec_router)
app.include_router(schedules_router)
app.include_router(notifications_router)
app.include_router(templates_router, prefix="/api/templates")


@app.get("/api/health")
async def health():
    from configforge.utils.paths import get_data_dir, get_configs_dir

    checks = {
        "status": "ok",
        "version": _get_version(),
    }

    # Check data directory writable
    data_dir = get_data_dir()
    try:
        os.makedirs(data_dir, exist_ok=True)
        test_file = os.path.join(data_dir, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks["data_dir_writable"] = True
    except Exception:
        checks["data_dir_writable"] = False
        checks["status"] = "degraded"

    # Check configs directory
    configs_dir = get_configs_dir()
    checks["configs_dir_exists"] = os.path.isdir(configs_dir)

    # Check scheduler
    try:
        from configforge.scheduler import _scheduler
        checks["scheduler_running"] = _scheduler.running if _scheduler else False
    except Exception:
        checks["scheduler_running"] = False

    # Check encryption key
    checks["encryption_key_set"] = bool(os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"))

    return checks

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
