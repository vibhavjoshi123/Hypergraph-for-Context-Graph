"""Together AI LLM connector.

Provides text completions, structured output, and embeddings via
Together AI's API (OpenAI-compatible). Used for fast classification
and cost-effective inference with open-weight models.

From ARCHITECTURE_PLAN.md Section 3.1 (P1).
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from src.llm.base import BaseLLMConnector, LLMConfig

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class TogetherConnector(BaseLLMConnector):
    """Together AI API connector.

    Uses Together AI's OpenAI-compatible API for inference with
    open-weight models (Llama, Mixtral, etc.) and embeddings.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            config
            or LLMConfig(
                provider="together",
                model="meta-llama/Llama-3-70b-chat-hf",
                base_url=TOGETHER_BASE_URL,
            )
        )
        self._client: object | None = None
        self._embedding_model: str = "togethercomputer/m2-bert-80M-8k-retrieval"

    async def _ensure_client(self) -> object:
        """Lazily initialize the Together AI client (OpenAI-compatible)."""
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or TOGETHER_BASE_URL,
                timeout=self.config.timeout,
            )
        except ImportError:
            logger.warning(
                "openai package not installed (required for Together AI). "
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
        """Generate a text completion using Together AI."""
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
        """Generate structured output matching a Pydantic schema."""
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
        """Generate embeddings using Together AI's embedding API."""
        client = await self._ensure_client()

        response = await client.embeddings.create(  # type: ignore[union-attr]
            model=self._embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]  # type: ignore[union-attr]
