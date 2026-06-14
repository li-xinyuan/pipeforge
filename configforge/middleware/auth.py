"""Simple API Key authentication middleware.

When CONFIGFORGE_API_KEY environment variable is set, all API requests
(except health check and static files) must include the key via
X-API-Key header or api_key query parameter.

If CONFIGFORGE_API_KEY is not set, authentication is disabled (dev mode).
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

API_KEY = os.environ.get("CONFIGFORGE_API_KEY", "")

# Paths that don't require authentication
PUBLIC_PATHS = {"/", "/api/health"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # No API key configured — auth disabled (dev mode)
        if not API_KEY:
            return await call_next(request)

        # Public paths don't require auth
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Static files don't require auth
        if request.url.path.startswith("/assets") or request.url.path.endswith((".js", ".css", ".ico", ".png", ".svg")):
            return await call_next(request)

        # Check API Key
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "code": "AUTH_FAILED"},
            )

        return await call_next(request)
