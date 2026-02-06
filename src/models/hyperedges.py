"""Hyperedge models for the context graph.

Hyperedges are n-ary relations connecting multiple entities in a single
atomic event. They map to TypeDB's relation types and implement the core
insight from the MIT paper: preserving irreducible multi-entity structure.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RelationType(StrEnum):
    """Types of hyperedge relations."""

    CONTEXT = "context-hyperedge"
    DECISION = "decision-event"
    ESCALATION = "escalation"
    APPROVAL = "approval"
    RENEWAL = "renewal"
    INCIDENT = "incident"


class RoleAssignment(BaseModel):
    """An entity's role within a hyperedge.

    In TypeDB terms: entity plays relation:role.
    """

    entity_id: str
    role: str = Field(..., description="The role this entity plays, e.g., 'customer', 'approver'")


class Hyperedge(BaseModel):
    """A hyperedge connecting N entities through typed roles.

    This is the core data structure: a single atomic n-ary relation.
    Maps to TypeDB's `context-hyperedge` relation type.

    From the Chemical Reaction Networks PDF:
    - In chemistry: a reaction event connecting all participants
    - In enterprise: a decision event connecting all participants
    """

    hyperedge_id: str = Field(..., description="Unique identifier for this hyperedge")
    relation_type: RelationType = Field(default=RelationType.CONTEXT)
    participants: list[RoleAssignment] = Field(
        ..., min_length=2, description="Entities and their roles in this hyperedge"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(default=1.0, ge=0, le=1)
    source_system: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @property
    def cardinality(self) -> int:
        """Number of entities in this hyperedge (edge size |e|)."""
        return len(self.participants)

    @property
    def entity_ids(self) -> set[str]:
        """Set of all entity IDs participating in this hyperedge."""
        return {p.entity_id for p in self.participants}

    def intersection_size(self, other: Hyperedge) -> int:
        """Compute intersection size (IS) with another hyperedge.

        IS >= 2 is the key constraint from the MIT paper for meaningful
        connectivity between hyperedges.
        """
        return len(self.entity_ids & other.entity_ids)

    def is_s_adjacent(self, other: Hyperedge, s: int = 2) -> bool:
        """Check if this hyperedge is s-adjacent to another.

        Two hyperedges are s-adjacent iff they share >= s nodes.
        """
        return self.intersection_size(other) >= s


class DecisionEvent(Hyperedge):
    """A decision event hyperedge - the key structure.

    From the architecture plan: connects involved entities with a decision maker,
    affected entities, and includes rationale.

    Isomorphic to chemical reactions (Chemical Reaction Networks PDF):
    - Participants = Reactants + Products + Catalysts
    - Rationale = Reaction mechanism
    - Decision type = Reaction type
    """

    relation_type: RelationType = RelationType.DECISION
    decision_type: str | None = Field(
        default=None, description="e.g., discount-approval, escalation, renewal"
    )
    rationale: str | None = Field(
        default=None, description="Decision reasoning / mechanism trace"
    )


class HypergraphPath(BaseModel):
    """A path through the hypergraph (chain of s-adjacent hyperedges).

    Isomorphic to:
    - Chemistry: reaction mechanism / metabolic pathway
    - Enterprise: precedent chain / decision trace
    - Category theory: s-walk / s-path (composition of morphisms)
    """

    hyperedges: list[Hyperedge] = Field(..., min_length=1)
    intersection_size: int = Field(default=2, ge=1, description="Minimum IS for adjacency")

    @property
    def length(self) -> int:
        """Number of hyperedges in the path."""
        return len(self.hyperedges)

    @property
    def all_entity_ids(self) -> set[str]:
        """All entity IDs involved across the entire path."""
        ids: set[str] = set()
        for he in self.hyperedges:
            ids |= he.entity_ids
        return ids

    def is_valid(self) -> bool:
        """Verify that consecutive hyperedges satisfy the IS constraint."""
        for i in range(len(self.hyperedges) - 1):
            if not self.hyperedges[i].is_s_adjacent(
                self.hyperedges[i + 1], self.intersection_size
            ):
                return False
        return True
