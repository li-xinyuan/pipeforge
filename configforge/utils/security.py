import re

_VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")


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
