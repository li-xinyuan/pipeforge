"""Centralised path configuration for ConfigForge.

All data / upload / log / output / config directories are resolved through
this module so that every part of the application honours the same
environment variables.
"""
import os


def get_data_dir() -> str:
    """Return the base data directory (env: CONFIGFORGE_DATA_DIR)."""
    return os.environ.get(
        "CONFIGFORGE_DATA_DIR",
        os.path.join(os.getcwd(), "data"),
    )


def get_configs_dir() -> str:
    """Return the configs directory (env: CONFIGFORGE_CONFIGS_DIR)."""
    return os.environ.get(
        "CONFIGFORGE_CONFIGS_DIR",
        os.path.join(os.getcwd(), "configs"),
    )


def get_upload_dir() -> str:
    """Return the temp uploads directory (env: CONFIGFORGE_UPLOAD_DIR)."""
    return os.environ.get("CONFIGFORGE_UPLOAD_DIR", "tmp/uploads")


def get_log_dir() -> str:
    """Return the temp logs directory (env: CONFIGFORGE_LOG_DIR)."""
    return os.environ.get("CONFIGFORGE_LOG_DIR", "tmp/logs")


def get_output_dir() -> str:
    """Return the pipeline output directory (env: CONFIGFORGE_OUTPUT_DIR)."""
    return os.environ.get(
        "CONFIGFORGE_OUTPUT_DIR",
        os.path.join(get_data_dir(), "outputs"),
    )


def get_pipeline_timeout() -> int:
    """Return pipeline timeout in seconds (env: CONFIGFORGE_PIPELINE_TIMEOUT)."""
    return int(os.environ.get("CONFIGFORGE_PIPELINE_TIMEOUT", "300"))
