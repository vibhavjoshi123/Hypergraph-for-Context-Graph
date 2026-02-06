"""Tests for configuration management."""

from src.config import (
    APISettings,
    ConnectorSettings,
    LLMSettings,
    Settings,
    TypeDBSettings,
    get_settings,
)


class TestTypeDBSettings:
    def test_defaults(self):
        s = TypeDBSettings()
        assert s.host == "localhost"
        assert s.port == 1729
        assert s.database == "context_graph"

    def test_address(self):
        s = TypeDBSettings()
        assert s.address == "localhost:1729"


class TestLLMSettings:
    def test_defaults(self):
        s = LLMSettings()
        assert s.default_provider == "anthropic"
        assert s.temperature == 0.0
        assert s.max_tokens == 4096


class TestAPISettings:
    def test_defaults(self):
        s = APISettings()
        assert s.port == 8000
        assert s.debug is False


class TestSettings:
    def test_get_settings(self):
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert isinstance(settings.typedb, TypeDBSettings)
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.connectors, ConnectorSettings)
        assert isinstance(settings.api, APISettings)
