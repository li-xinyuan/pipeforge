"""JWT token utilities with fallback when PyJWT is not installed."""

import hmac
import hashlib
import json
import os
import time
import base64

_TOKEN_TTL = 86400  # 24 hours

try:
    import jwt  # PyJWT
    _HAS_PYJWT = True
except ImportError:
    _HAS_PYJWT = False


def _get_jwt_secret() -> str:
    """Get JWT secret from environment (dynamic, not cached at import time)."""
    return os.environ.get("CONFIGFORGE_JWT_SECRET", "")


def is_jwt_enabled() -> bool:
    """Return True if JWT authentication is configured."""
    return bool(_get_jwt_secret())


def create_token(payload: dict) -> str:
    """Create a signed JWT token."""
    secret = _get_jwt_secret()
    if _HAS_PYJWT:
        return jwt.encode(payload, secret, algorithm="HS256")

    # Fallback: simple HMAC-signed token
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    signing_input = f"{header}.{body}"
    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{signing_input}.{sig}"


def decode_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None if invalid/expired."""
    secret = _get_jwt_secret()
    if _HAS_PYJWT:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except Exception:
            return None

    # Fallback: verify HMAC signature manually
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{body_b64}"
        expected_sig = hmac.new(
            secret.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body_b64 + "=="))
    except Exception:
        return None

    # Check expiration
    exp = payload.get("exp")
    if exp and time.time() > exp:
        return None

    return payload


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
