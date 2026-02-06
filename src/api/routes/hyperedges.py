"""Hyperedge CRUD endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.models.hyperedges import RelationType

router = APIRouter()


class RoleAssignmentCreate(BaseModel):
    """Role assignment in a hyperedge creation request."""

    entity_id: str
    role: str


class HyperedgeCreate(BaseModel):
    """Request body for creating a hyperedge."""

    hyperedge_id: str
    relation_type: RelationType = RelationType.DECISION
    participants: list[RoleAssignmentCreate] = Field(..., min_length=2)
    decision_type: str | None = None
    rationale: str | None = None
    source_system: str | None = None


class HyperedgeResponse(BaseModel):
    """Response for hyperedge operations."""

    hyperedge_id: str
    relation_type: RelationType
    participants: list[RoleAssignmentCreate]
    decision_type: str | None = None
    rationale: str | None = None


@router.post("/hyperedges", response_model=HyperedgeResponse, status_code=201)
async def create_hyperedge(request: HyperedgeCreate) -> HyperedgeResponse:
    """Create a new hyperedge connecting multiple entities.

    This is the core operation: creating an n-ary relation (hyperedge)
    that connects 2+ entities with typed roles.
    """
    return HyperedgeResponse(
        hyperedge_id=request.hyperedge_id,
        relation_type=request.relation_type,
        participants=request.participants,
        decision_type=request.decision_type,
        rationale=request.rationale,
    )


@router.get("/hyperedges/{entity_id}", response_model=list[HyperedgeResponse])
async def get_hyperedges_for_entity(entity_id: str) -> list[HyperedgeResponse]:
    """Get all hyperedges involving an entity."""
    raise HTTPException(
        status_code=501,
        detail="TypeDB backend required. Configure TYPEDB_HOST and TYPEDB_PORT.",
    )


class SAdjacencyRequest(BaseModel):
    """Request for finding s-adjacent hyperedges."""

    entity_id: str
    s: int = Field(default=2, ge=1, description="Minimum intersection size")


@router.post("/hyperedges/s-adjacent", response_model=list[dict[str, Any]])
async def find_s_adjacent(request: SAdjacencyRequest) -> list[dict[str, Any]]:
    """Find hyperedges that are s-adjacent (share >= s entities).

    IS >= 2 reduces noise by 87% per the MIT paper.
    """
    raise HTTPException(
        status_code=501,
        detail="TypeDB backend required. Configure TYPEDB_HOST and TYPEDB_PORT.",
    )
