import json
import os

_SETTINGS_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "ai_settings.json")


def load_settings() -> "AiSettings":
    from configforge.models.ai import AiSettings
    if not os.path.exists(SETTINGS_FILE):
        return AiSettings()
    with open(SETTINGS_FILE, "r") as f:
        raw = json.load(f)
    return AiSettings(**raw)


def save_settings(settings: "AiSettings") -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)


def mask_key(key: str) -> str:
    if not key or len(key) <= 6:
        return key
    return key[:3] + "***" + key[-3:]
