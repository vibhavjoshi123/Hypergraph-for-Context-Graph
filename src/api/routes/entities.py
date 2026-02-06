"""Entity CRUD endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.models.entities import EntityType

router = APIRouter()


class EntityCreate(BaseModel):
    """Request body for creating an entity."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    source_system: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EntityResponse(BaseModel):
    """Response for entity operations."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    source_system: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


@router.post("/entities", response_model=EntityResponse, status_code=201)
async def create_entity(request: EntityCreate) -> EntityResponse:
    """Create a new entity in the hypergraph."""
    return EntityResponse(
        entity_id=request.entity_id,
        entity_name=request.entity_name,
        entity_type=request.entity_type,
        source_system=request.source_system,
        attributes=request.attributes,
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str) -> EntityResponse:
    """Get an entity by ID."""
    raise HTTPException(
        status_code=501,
        detail="TypeDB backend required. Configure TYPEDB_HOST and TYPEDB_PORT.",
    )


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(entity_type: EntityType | None = None) -> list[EntityResponse]:
    """List entities, optionally filtered by type."""
    raise HTTPException(
        status_code=501,
        detail="TypeDB backend required. Configure TYPEDB_HOST and TYPEDB_PORT.",
    )


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_entity(entity_id: str) -> None:
    """Delete an entity by ID."""
    raise HTTPException(
        status_code=501,
        detail="TypeDB backend required. Configure TYPEDB_HOST and TYPEDB_PORT.",
    )
