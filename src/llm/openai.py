"""OpenAI GPT / Embeddings connector.

Provides text completions, structured output, and embedding generation
via the OpenAI Chat Completions and Embeddings APIs.

From ARCHITECTURE_PLAN.md Section 3.2 - used for embeddings
(text-embedding-3-large) and as fallback for extraction tasks.
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from src.llm.base import BaseLLMConnector, LLMConfig

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class OpenAIConnector(BaseLLMConnector):
    """OpenAI API connector for GPT models and embeddings."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            config
            or LLMConfig(
                provider="openai",
                model="gpt-4o",
            )
        )
        self._client: object | None = None
        self._embedding_model: str = "text-embedding-3-large"

    async def _ensure_client(self) -> object:
        """Lazily initialize the OpenAI client."""
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI

            kwargs: dict = {"timeout": self.config.timeout}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url

            self._client = AsyncOpenAI(**kwargs)
        except ImportError:
            logger.warning(
                "openai package not installed. "
                "Install with: pip install openai"
            )
            raise

        return self._client

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str:
        """Generate a text completion using GPT."""
        client = await self._ensure_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(  # type: ignore[union-attr]
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""  # type: ignore[union-attr]

    async def complete_structured(
        self,
        prompt: str,
        output_schema: type[T],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Uses GPT's JSON mode with schema instructions.
        """
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```"
        )

        system = system_prompt or ""
        system += "\nYou must respond with valid JSON only. No markdown, no explanation."

        raw = await self.complete(structured_prompt, system_prompt=system.strip())

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3].strip()

        return output_schema.model_validate_json(text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI's embedding API."""
        client = await self._ensure_client()

        response = await client.embeddings.create(  # type: ignore[union-attr]
            model=self._embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]  # type: ignore[union-attr]
