"""Tests for LLM connector interfaces."""

import pytest

from src.llm.anthropic import AnthropicConnector
from src.llm.base import LLMConfig
from src.llm.openai import OpenAIConnector
from src.llm.together import TogetherConnector


class TestAnthropicConnector:
    def test_default_config(self):
        connector = AnthropicConnector()
        assert connector.config.provider == "anthropic"
        assert "claude" in connector.config.model

    def test_custom_config(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-opus-4-20250514",
            max_tokens=8192,
        )
        connector = AnthropicConnector(config)
        assert connector.config.model == "claude-opus-4-20250514"
        assert connector.config.max_tokens == 8192

    @pytest.mark.asyncio
    async def test_embed_not_supported(self):
        connector = AnthropicConnector()
        with pytest.raises(NotImplementedError):
            await connector.embed(["test"])


class TestOpenAIConnector:
    def test_default_config(self):
        connector = OpenAIConnector()
        assert connector.config.provider == "openai"
        assert connector.config.model == "gpt-4o"

    def test_custom_config(self):
        config = LLMConfig(
            provider="openai",
            model="gpt-4-turbo",
            temperature=0.5,
        )
        connector = OpenAIConnector(config)
        assert connector.config.model == "gpt-4-turbo"
        assert connector.config.temperature == 0.5


class TestTogetherConnector:
    def test_default_config(self):
        connector = TogetherConnector()
        assert connector.config.provider == "together"
        assert "llama" in connector.config.model.lower() or "Llama" in connector.config.model

    def test_base_url(self):
        connector = TogetherConnector()
        assert connector.config.base_url == "https://api.together.xyz/v1"
