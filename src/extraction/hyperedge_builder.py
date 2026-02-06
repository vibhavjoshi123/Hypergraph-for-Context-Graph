"""Hyperedge builder for constructing hyperedges from extraction results.

Takes ExtractionResults (entities + relationships) and constructs
properly typed Hyperedge and DecisionEvent objects ready for insertion
into the TypeDB hypergraph.

From ARCHITECTURE_PLAN.md Section 3.4 and project structure.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from src.extraction.entity_resolver import EntityResolver, ResolvedEntity
from src.extraction.pipeline import ExtractionResult
from src.models.hyperedges import (
    DecisionEvent,
    Hyperedge,
    RelationType,
    RoleAssignment,
)

logger = logging.getLogger(__name__)

# Map extracted relation types to internal RelationType
RELATION_TYPE_MAP: dict[str, RelationType] = {
    "context-hyperedge": RelationType.CONTEXT,
    "decision-event": RelationType.DECISION,
    "escalation": RelationType.ESCALATION,
    "approval": RelationType.APPROVAL,
    "renewal": RelationType.RENEWAL,
    "incident": RelationType.INCIDENT,
}


class HyperedgeBuilder:
    """Builds Hyperedge objects from extraction results.

    Resolves entity references via the EntityResolver, then constructs
    typed hyperedges connecting the resolved entities.
    """

    def __init__(self, resolver: EntityResolver | None = None) -> None:
        self._resolver = resolver or EntityResolver()

    async def build_from_extraction(
        self,
        result: ExtractionResult,
    ) -> list[Hyperedge]:
        """Build hyperedges from an extraction result.

        Resolves all entities, then constructs hyperedges for each
        extracted relationship.
        """
        if not result.relationships:
            return []

        # Resolve entities first
        entity_map: dict[str, ResolvedEntity] = {}
        source_system = result.source_system or "unknown"
        for entity in result.entities:
            resolved = await self._resolver.resolve(entity, source_system)
            entity_map[entity.entity_id] = resolved

        # Build hyperedges
        hyperedges: list[Hyperedge] = []
        for rel in result.relationships:
            hyperedge = self._build_single(rel, entity_map, source_system)
            if hyperedge:
                hyperedges.append(hyperedge)

        logger.info(
            "Built %d hyperedge(s) from extraction result (source=%s)",
            len(hyperedges),
            source_system,
        )
        return hyperedges

    async def build_batch(
        self,
        results: list[ExtractionResult],
    ) -> list[Hyperedge]:
        """Build hyperedges from multiple extraction results."""
        all_hyperedges: list[Hyperedge] = []
        for result in results:
            hyperedges = await self.build_from_extraction(result)
            all_hyperedges.extend(hyperedges)
        return all_hyperedges

    def _build_single(
        self,
        relationship: object,
        entity_map: dict[str, ResolvedEntity],
        source_system: str,
    ) -> Hyperedge | None:
        """Build a single hyperedge from an extracted relationship."""
        # relationship is an ExtractedRelationship (duck-typed)
        rel_type_str = getattr(relationship, "relation_type", "context-hyperedge")
        participants_data = getattr(relationship, "participants", [])
        attributes = getattr(relationship, "attributes", {})

        if len(participants_data) < 2:
            logger.warning(
                "Skipping relationship with fewer than 2 participants: %s",
                rel_type_str,
            )
            return None

        # Map relation type
        relation_type = RELATION_TYPE_MAP.get(rel_type_str, RelationType.CONTEXT)

        # Build role assignments
        role_assignments: list[RoleAssignment] = []
        for p in participants_data:
            eid = p.get("entity_id", "") if isinstance(p, dict) else getattr(p, "entity_id", "")
            role = (
                p.get("role", "participant")
                if isinstance(p, dict)
                else getattr(p, "role", "participant")
            )

            # Use resolved entity ID if available
            resolved = entity_map.get(eid)
            canonical_id = resolved.canonical_id if resolved else eid

            role_assignments.append(
                RoleAssignment(entity_id=canonical_id, role=role)
            )

        hyperedge_id = f"he_{uuid.uuid4().hex[:12]}"

        # Create DecisionEvent for decision-type relations
        if relation_type in (
            RelationType.DECISION,
            RelationType.ESCALATION,
            RelationType.APPROVAL,
            RelationType.RENEWAL,
            RelationType.INCIDENT,
        ):
            return DecisionEvent(
                hyperedge_id=hyperedge_id,
                relation_type=relation_type,
                participants=role_assignments,
                timestamp=datetime.utcnow(),
                source_system=source_system,
                decision_type=attributes.get("decision_type"),
                rationale=attributes.get("rationale"),
            )

        return Hyperedge(
            hyperedge_id=hyperedge_id,
            relation_type=relation_type,
            participants=role_assignments,
            timestamp=datetime.utcnow(),
            source_system=source_system,
        )
