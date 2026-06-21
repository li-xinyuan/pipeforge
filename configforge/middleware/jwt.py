"""JWT token utilities."""

import os
import time

import jwt

_TOKEN_TTL = 86400  # 24 hours


def _get_jwt_secret() -> str:
    """Get JWT secret from environment (dynamic, not cached at import time)."""
    return os.environ.get("CONFIGFORGE_JWT_SECRET", "")


def is_jwt_enabled() -> bool:
    """Return True if JWT authentication is configured."""
    return bool(_get_jwt_secret())


def create_token(payload: dict) -> str:
    """Create a signed JWT token."""
    secret = _get_jwt_secret()
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None if invalid/expired."""
    secret = _get_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None


def create_access_token(user_id: str, username: str, role: str) -> str:
    """Create a standard access token for a user."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + _TOKEN_TTL,
    }
    return create_token(payload)
