"""Environment detection utilities for ConfigForge."""

import os

_ENV_VAR = "CONFIGFORGE_ENV"
_DEFAULT_ENV = "development"


def get_env() -> str:
    """Return the current environment name string.

    Reads the ``CONFIGFORGE_ENV`` environment variable, defaulting to
    ``"development"`` when not set.
    """
    return os.environ.get(_ENV_VAR, _DEFAULT_ENV)


def is_production() -> bool:
    """Return ``True`` when running in production mode."""
    return get_env() == "production"


def is_development() -> bool:
    """Return ``True`` when *not* in production mode."""
    return not is_production()
