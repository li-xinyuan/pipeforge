import re

_VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")

# SQL identifier whitelist: Unicode letters, digits, underscores
_SQL_ID_RE = re.compile(r"^[\w][\w]{0,63}$")


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
