import pytest
from pydantic import ValidationError

from configforge.models.ai import AiProvider, AiSettings, AiSettingsUpdate


class TestAiProvider:
    def test_openai(self):
        assert AiProvider.OPENAI == "openai"

    def test_anthropic(self):
        assert AiProvider.ANTHROPIC == "anthropic"

    def test_custom(self):
        assert AiProvider.CUSTOM == "custom"


class TestAiSettings:
    def test_defaults(self):
        s = AiSettings()
        assert s.provider == AiProvider.OPENAI
        assert s.api_key == ""
        assert s.base_url == ""
        assert s.model == ""
        assert s.temperature == pytest.approx(0.7)
        assert s.max_tokens == 4096
        assert s.enabled is False

    def test_valid_settings(self):
        s = AiSettings(provider="anthropic", api_key="sk-ant-123", model="claude-sonnet-4-6", temperature=1.0, max_tokens=8192, enabled=True)
        assert s.provider == "anthropic"
        assert s.temperature == pytest.approx(1.0)

    def test_temperature_below_min_raises(self):
        with pytest.raises(ValidationError):
            AiSettings(temperature=-0.1)

    def test_temperature_above_max_raises(self):
        with pytest.raises(ValidationError):
            AiSettings(temperature=2.1)

    def test_max_tokens_below_min_raises(self):
        with pytest.raises(ValidationError):
            AiSettings(max_tokens=255)

    def test_max_tokens_above_max_raises(self):
        with pytest.raises(ValidationError):
            AiSettings(max_tokens=128001)

    def test_api_key_max_length(self):
        s = AiSettings(api_key="a" * 512)
        assert len(s.api_key) == 512

    def test_api_key_exceeds_max_length_raises(self):
        with pytest.raises(ValidationError):
            AiSettings(api_key="a" * 513)


class TestAiSettingsUpdate:
    def test_defaults(self):
        u = AiSettingsUpdate()
        assert u.provider == AiProvider.OPENAI
        assert u.api_key is None  # None = keep old value, not "" = clear
        assert u.enabled is False

    def test_explicit_empty_api_key_clears(self):
        u = AiSettingsUpdate(api_key="")
        assert u.api_key == ""

    def test_explicit_api_key_updates(self):
        u = AiSettingsUpdate(api_key="new-key-123")
        assert u.api_key == "new-key-123"

    def test_api_key_none_preserves(self):
        u = AiSettingsUpdate()
        assert u.api_key is None
