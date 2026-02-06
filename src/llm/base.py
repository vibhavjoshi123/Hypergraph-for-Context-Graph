"""Abstract base LLM connector.

Provides a uniform interface for LLM providers (Anthropic Claude, OpenAI GPT-4,
Together AI, etc.) supporting both text completions and structured output.

From ARCHITECTURE_PLAN.md Section 3.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMConfig(BaseModel):
    """Configuration for an LLM connector."""

    provider: str  # "anthropic", "openai", "together", "local"
    model: str
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.0, ge=0, le=2)
    timeout: int = Field(default=60, ge=1)


class BaseLLMConnector(ABC):
    """Abstract base class for LLM connectors.

    All LLM providers implement this interface to provide:
    - Text completion (free-form generation)
    - Structured output (Pydantic model generation)
    - Embedding generation
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str:
        """Generate a text completion.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instructions.

        Returns:
            Generated text string.
        """
        ...

    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        output_schema: type[T],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Args:
            prompt: The user prompt.
            output_schema: Pydantic model class for the expected output.
            system_prompt: Optional system instructions.

        Returns:
            Instance of the output_schema model.
        """
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (list of floats).
        """
        ...
