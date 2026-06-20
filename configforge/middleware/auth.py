"""Simple API Key / JWT authentication middleware.

When CONFIGFORGE_JWT_SECRET environment variable is set, JWT-based
authentication is enabled: all API requests (except health check,
auth endpoints, and static files) must include a valid Bearer token
in the Authorization header.

When CONFIGFORGE_API_KEY environment variable is set (and JWT is not
enabled), all API requests must include the key via X-API-Key header.

If neither is set, authentication is disabled (dev mode).
"""
import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _get_api_key() -> str:
    """Get API key from environment (dynamic, not cached at import time)."""
    return os.environ.get("CONFIGFORGE_API_KEY", "")

# Paths that don't require authentication
PUBLIC_PATHS = {"/", "/api/health"}

# Paths that are public when JWT auth is enabled (login/register)
JWT_PUBLIC_PATHS = {"/api/auth/login", "/api/auth/register"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        jwt_secret = os.environ.get("CONFIGFORGE_JWT_SECRET", "")
        api_key = _get_api_key()

        # No auth configured — auth disabled (dev mode)
        if not api_key and not jwt_secret:
            return await call_next(request)

        # Public paths don't require auth
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Static files don't require auth
        if request.url.path.startswith("/assets") or request.url.path.endswith((".js", ".css", ".ico", ".png", ".svg")):
            return await call_next(request)

        # JWT authentication mode
        if jwt_secret:
            # Auth endpoints are public (login/register need to be accessible without token)
            if request.url.path in JWT_PUBLIC_PATHS:
                return await call_next(request)

            # All other endpoints (including /api/auth/me) require a valid JWT
            from configforge.middleware.jwt import decode_token

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: Bearer token required", "code": "AUTH_FAILED"},
                )

            token = auth_header[7:]
            payload = decode_token(token)
            if not payload:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: invalid or expired token", "code": "AUTH_FAILED"},
                )

            return await call_next(request)

        # API Key authentication mode (original behavior)
        key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(key, api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "code": "AUTH_FAILED"},
            )

        return await call_next(request)
