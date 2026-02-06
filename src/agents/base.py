"""Base agent interface for the multi-agent reasoning system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentQuery(BaseModel):
    """Input query for an agent."""

    query: str = Field(..., description="Natural language query")
    context: dict[str, Any] = Field(default_factory=dict)
    max_depth: int = Field(default=5, ge=1)
    intersection_size: int = Field(default=2, ge=1)


class AgentResponse(BaseModel):
    """Response from an agent."""

    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    paths_found: int = 0
    confidence: float = Field(default=0.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for reasoning agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name identifier."""
        ...

    @abstractmethod
    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a query and return a response.

        Args:
            query: The agent query with parameters.

        Returns:
            AgentResponse with answer, evidence, and metadata.
        """
        ...
