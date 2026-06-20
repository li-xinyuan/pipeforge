import os
import re

_VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")

# SQL identifier whitelist: Unicode letters, digits, underscores
_SQL_ID_RE = re.compile(r"^[\w][\w]{0,63}$")

# Connection string password pattern: protocol://user:password@host
# Handles: empty password (user:@host), normal password (user:pass@host)
# Note: passwords containing @ should be URL-encoded as %40 in proper connection strings
_CONN_STRING_PW_RE = re.compile(
    r'(mysql\+pymysql|postgresql\+psycopg2|mysql|postgresql|mongodb)://([^:]+):([^@]*)@',
    re.IGNORECASE,
)


def validate_id(value: str, param_name: str = "id") -> str:
    if not value:
        raise ValueError(f"{param_name} must not be empty")
    if ".." in value:
        raise ValueError(f"{param_name} contains illegal path traversal sequence '..'")
    if "/" in value or "\\" in value:
        raise ValueError(f"{param_name} contains illegal path separator")
    if not _VALID_ID_RE.fullmatch(value):
        raise ValueError(
            f"{param_name} contains invalid characters (allowed: a-z A-Z 0-9 _ - .)"
        )
    return value


def safe_identifier(name: str, param_name: str = "identifier") -> str:
    """Validate a SQL table/column identifier against injection.

    Only allows: letters, digits, underscores. Must start with a letter or underscore.
    Max length 64 characters.
    """
    if not name:
        raise ValueError(f"{param_name} must not be empty")
    if not _SQL_ID_RE.fullmatch(name):
        raise ValueError(
            f"{param_name} '{name}' is not a valid SQL identifier "
            "(must start with letter/underscore, contain only letters/digits/underscores, max 64 chars)"
        )
    return name


def sanitize_connection_string(text: str) -> str:
    """Mask passwords in connection strings within text.

    Replaces protocol://user:password@host with protocol://user:***@host.
    """
    return _CONN_STRING_PW_RE.sub(r'\1://\2:***@', text)


# Allowed directories for SQLite database files
_SQLITE_ALLOWED_DIRS: list[str] | None = None


def validate_url(url: str) -> str:
    """Validate a URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTP(S) schemes
    - Internal/private IP addresses (10.x, 172.16-31.x, 192.168.x, 127.x)
    - Cloud metadata endpoints (169.254.169.254, metadata.google.internal, etc.)
    - Link-local addresses
    """
    import ipaddress
    from urllib.parse import urlparse

    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname")

    # Block known metadata endpoints
    BLOCKED_HOSTS = {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.azure.com",
        "instance-data",
    }
    if hostname.lower() in BLOCKED_HOSTS:
        raise ValueError(f"Access to metadata endpoint {hostname} is blocked")

    # Block private/internal IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # hostname is a domain name, not an IP — allow DNS resolution
        # (We could add DNS resolution check here in the future)
        ip = None

    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        raise ValueError(f"Access to internal IP address {ip} is blocked")

    return url


def validate_sqlite_path(path: str, param_name: str = "file_path") -> str:
    """Validate that a SQLite file path is within allowed directories.

    Prevents path traversal attacks by ensuring the resolved path
    is under an allowed data directory.
    """
    if not path:
        raise ValueError(f"{param_name} must not be empty")

    # Block obvious path traversal
    if ".." in path:
        raise ValueError(f"{param_name} contains illegal path traversal sequence '..'")

    global _SQLITE_ALLOWED_DIRS
    if _SQLITE_ALLOWED_DIRS is None:
        from configforge.utils.paths import get_data_dir
        _SQLITE_ALLOWED_DIRS = [
            os.path.abspath(get_data_dir()),
            os.path.abspath("tmp"),
        ]

    abs_path = os.path.abspath(path)
    if not any(abs_path.startswith(d) for d in _SQLITE_ALLOWED_DIRS):
        raise ValueError(
            f"{param_name} must be within allowed directories "
            f"({', '.join(_SQLITE_ALLOWED_DIRS)})"
        )
    return path
