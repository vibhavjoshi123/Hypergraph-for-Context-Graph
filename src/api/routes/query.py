"""Query endpoint for natural language queries against the hypergraph."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class QueryRequest(BaseModel):
    """Natural language query request."""

    query: str = Field(..., description="Natural language query", min_length=1)
    intersection_size: int = Field(default=2, ge=1, description="Minimum IS for path finding")
    max_depth: int = Field(default=5, ge=1, description="Maximum traversal depth")
    k_paths: int = Field(default=3, ge=1, description="Number of paths to find")


class QueryResponse(BaseModel):
    """Response to a natural language query."""

    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    paths_found: int = 0
    confidence: float = 0.0


@router.post("/query", response_model=QueryResponse)
async def query_context_graph(request: QueryRequest) -> QueryResponse:
    """Query the context graph with a natural language question.

    Example: "Why was Acme Corp given a 20% discount?"
    """
    return QueryResponse(
        answer=(
            f"Query received: '{request.query}'. "
            "TypeDB backend required for full query processing. "
            "Connect a TypeDB instance and configure LLM providers to enable "
            "multi-agent reasoning (Context -> Executive -> Governance)."
        ),
        paths_found=0,
        confidence=0.0,
    )
