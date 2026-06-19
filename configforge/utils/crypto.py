"""Centralised Fernet cipher management for ConfigForge."""

import hashlib
import logging
import os
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet

from configforge.utils.paths import get_data_dir

logger = logging.getLogger(__name__)

_warned_no_env_key = False


def get_cipher() -> Fernet:
    """Return a Fernet cipher for encrypting/decrypting secrets.

    Priority:
    1. CONFIGFORGE_ENCRYPTION_KEY environment variable
    2. Auto-generated .fernet_key file in data directory
    3. Generate new key and save to .fernet_key
    """
    global _warned_no_env_key

    raw = os.environ.get("CONFIGFORGE_ENCRYPTION_KEY", "")
    if raw:
        key = urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
        return Fernet(key)

    # No env key set — use file-based key
    data_dir = get_data_dir()
    key_path = os.path.join(data_dir, ".fernet_key")

    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(data_dir, exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        logger.warning(
            "CONFIGFORGE_ENCRYPTION_KEY not set. Auto-generated .fernet_key at %s. "
            "This key will be lost if the container is restarted, making all "
            "encrypted credentials (database passwords, API keys, SMTP passwords) "
            "unrecoverable. Set CONFIGFORGE_ENCRYPTION_KEY in production!",
            key_path,
        )

    if not _warned_no_env_key:
        _warned_no_env_key = True
        logger.warning(
            "CONFIGFORGE_ENCRYPTION_KEY environment variable is not set. "
            "Using auto-generated key file. This is NOT recommended for production."
        )

    return Fernet(key)
