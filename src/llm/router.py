"""LLM routing logic for task-based model selection.

Routes requests to the appropriate LLM provider based on the task type.
Supports fallback chains for reliability.

From ARCHITECTURE_PLAN.md Section 3.3.
"""

from __future__ import annotations

import logging
from typing import TypeVar

from pydantic import BaseModel

from src.llm.base import BaseLLMConnector

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

# Default task-to-provider routing
DEFAULT_ROUTING: dict[str, str] = {
    "extraction": "anthropic",
    "reasoning": "anthropic",
    "embedding": "openai",
    "fast_classification": "together",
}


class LLMRouter:
    """Routes LLM requests to appropriate providers based on task type.

    From ARCHITECTURE_PLAN.md Section 3.2:
    - Entity Extraction -> Claude 3.5 Sonnet / GPT-4o
    - Relation Identification -> Claude 3.5 Sonnet
    - Reasoning/Interpretation -> Claude Opus
    - Embeddings -> text-embedding-3-large
    """

    def __init__(
        self,
        connectors: dict[str, BaseLLMConnector],
        routing: dict[str, str] | None = None,
    ) -> None:
        self.connectors = connectors
        self.task_routing = routing or DEFAULT_ROUTING

    async def route(
        self,
        task: str,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str:
        """Route a completion request to the appropriate provider.

        Args:
            task: Task type (e.g., "extraction", "reasoning").
            prompt: The user prompt.
            system_prompt: Optional system instructions.

        Returns:
            Generated text from the selected provider.
        """
        provider = self.task_routing.get(task, "anthropic")
        connector = self._get_connector(provider)
        return await connector.complete(prompt, system_prompt, **kwargs)

    async def route_structured(
        self,
        task: str,
        prompt: str,
        output_schema: type[T],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> T:
        """Route a structured output request to the appropriate provider."""
        provider = self.task_routing.get(task, "anthropic")
        connector = self._get_connector(provider)
        return await connector.complete_structured(
            prompt, output_schema, system_prompt, **kwargs
        )

    async def embed(self, texts: list[str], provider: str | None = None) -> list[list[float]]:
        """Route an embedding request."""
        provider = provider or self.task_routing.get("embedding", "openai")
        connector = self._get_connector(provider)
        return await connector.embed(texts)

    def _get_connector(self, provider: str) -> BaseLLMConnector:
        """Get a connector by provider name, with fallback."""
        if provider in self.connectors:
            return self.connectors[provider]
        # Fall back to any available connector
        if self.connectors:
            fallback = next(iter(self.connectors))
            logger.warning(
                "Provider '%s' not available, falling back to '%s'",
                provider,
                fallback,
            )
            return self.connectors[fallback]
        raise ValueError("No LLM connectors configured")
