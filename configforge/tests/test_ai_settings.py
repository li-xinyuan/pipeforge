import os
import tempfile

from configforge.models.ai import AiProvider, AiSettings
from configforge.services.ai.settings import load_settings, mask_key, save_settings


def test_load_defaults():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path)  # ensure file does not exist, so defaults are returned
    try:
        import configforge.services.ai.settings as mod
        orig = mod.SETTINGS_FILE
        mod.SETTINGS_FILE = path
        settings = load_settings()
        assert settings.enabled is False
        assert settings.provider == AiProvider.OPENAI
        assert settings.api_key == ""
        mod.SETTINGS_FILE = orig
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_save_and_load():
    settings = AiSettings(provider=AiProvider.ANTHROPIC, api_key="sk-test-key", enabled=True, model="claude-sonnet-4-6")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        pass
    try:
        import configforge.services.ai.settings as mod
        orig = mod.SETTINGS_FILE
        mod.SETTINGS_FILE = f.name
        save_settings(settings)
        loaded = load_settings()
        assert loaded.provider == AiProvider.ANTHROPIC
        assert loaded.api_key == "sk-test-key"
        assert loaded.model == "claude-sonnet-4-6"
        assert loaded.enabled is True
        mod.SETTINGS_FILE = orig
    finally:
        os.unlink(f.name)


def test_mask_key():
    assert mask_key("sk-abc123def456") == "sk-***456"
    assert mask_key("short") == "short"
    assert mask_key("") == ""
