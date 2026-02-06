"""Entity resolution across multiple data sources.

Matches and merges entity references from different enterprise systems
(Salesforce, Zendesk, Slack, etc.) using embedding similarity and
LLM-powered matching.

From ARCHITECTURE_PLAN.md Section 3.2: Entity Resolution uses
Embedding + LLM to match entities across systems.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.extraction.pipeline import ExtractedEntity
from src.llm.base import BaseLLMConnector
from src.llm.prompts.resolution import ENTITY_MATCH_PROMPT, RESOLUTION_SYSTEM

logger = logging.getLogger(__name__)


class EntityMatch(BaseModel):
    """Result of comparing two entity references."""

    entity_a_id: str
    entity_b_id: str
    is_match: bool
    confidence: float = Field(ge=0, le=1)
    reasoning: str = ""
    matched_fields: list[str] = Field(default_factory=list)
    conflicting_fields: list[str] = Field(default_factory=list)


class ResolvedEntity(BaseModel):
    """A resolved entity with merged data from multiple sources."""

    canonical_id: str
    canonical_name: str
    entity_type: str
    source_ids: dict[str, str] = Field(
        default_factory=dict,
        description="source_system -> original_id mapping",
    )
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0, le=1)


class EntityResolver:
    """Resolves entity references across enterprise data sources.

    Uses a combination of:
    1. Exact ID matching (when cross-system IDs are available)
    2. Name-based fuzzy matching
    3. Embedding similarity (when vectors are available)
    4. LLM-powered disambiguation (for ambiguous cases)
    """

    def __init__(
        self,
        llm: BaseLLMConnector | None = None,
        similarity_threshold: float = 0.85,
    ) -> None:
        self._llm = llm
        self._similarity_threshold = similarity_threshold
        self._known_entities: dict[str, ResolvedEntity] = {}

    @property
    def known_entities(self) -> dict[str, ResolvedEntity]:
        """All currently resolved entities."""
        return dict(self._known_entities)

    async def resolve(
        self,
        entity: ExtractedEntity,
        source_system: str,
    ) -> ResolvedEntity:
        """Resolve an extracted entity against known entities.

        Returns an existing ResolvedEntity if a match is found,
        or creates a new one.
        """
        # Try exact ID match first
        for resolved in self._known_entities.values():
            if (
                source_system in resolved.source_ids
                and resolved.source_ids[source_system] == entity.entity_id
            ):
                return resolved

        # Try name-based matching
        match = self._find_by_name(entity)
        if match:
            match.source_ids[source_system] = entity.entity_id
            match.attributes.update(entity.attributes)
            return match

        # If LLM available, try semantic matching for ambiguous cases
        if self._llm and self._known_entities:
            llm_match = await self._llm_resolve(entity, source_system)
            if llm_match:
                return llm_match

        # No match found - create new resolved entity
        resolved = ResolvedEntity(
            canonical_id=entity.entity_id,
            canonical_name=entity.entity_name,
            entity_type=entity.entity_type,
            source_ids={source_system: entity.entity_id},
            attributes=entity.attributes,
        )
        self._known_entities[resolved.canonical_id] = resolved
        return resolved

    async def resolve_batch(
        self,
        entities: list[ExtractedEntity],
        source_system: str,
    ) -> list[ResolvedEntity]:
        """Resolve a batch of entities."""
        results: list[ResolvedEntity] = []
        for entity in entities:
            resolved = await self.resolve(entity, source_system)
            results.append(resolved)
        return results

    def _find_by_name(self, entity: ExtractedEntity) -> ResolvedEntity | None:
        """Find a matching resolved entity by normalized name."""
        normalized = entity.entity_name.strip().lower()
        for resolved in self._known_entities.values():
            if resolved.entity_type != entity.entity_type:
                continue
            if resolved.canonical_name.strip().lower() == normalized:
                return resolved
        return None

    async def _llm_resolve(
        self,
        entity: ExtractedEntity,
        source_system: str,
    ) -> ResolvedEntity | None:
        """Use LLM to resolve ambiguous entity matches."""
        if not self._llm:
            return None

        # Find candidates of the same type
        candidates = [
            r for r in self._known_entities.values()
            if r.entity_type == entity.entity_type
        ]
        if not candidates:
            return None

        # Check top candidates via LLM
        for candidate in candidates[:5]:
            prompt = ENTITY_MATCH_PROMPT.format(
                source_a=source_system,
                entity_a_id=entity.entity_id,
                entity_a_name=entity.entity_name,
                entity_a_type=entity.entity_type,
                entity_a_attrs=entity.attributes,
                source_b=next(iter(candidate.source_ids), "unknown"),
                entity_b_id=candidate.canonical_id,
                entity_b_name=candidate.canonical_name,
                entity_b_type=candidate.entity_type,
                entity_b_attrs=candidate.attributes,
            )

            try:
                result = await self._llm.complete_structured(
                    prompt=prompt,
                    output_schema=EntityMatch,
                    system_prompt=RESOLUTION_SYSTEM,
                )
                if result.is_match and result.confidence >= self._similarity_threshold:
                    candidate.source_ids[source_system] = entity.entity_id
                    candidate.attributes.update(entity.attributes)
                    logger.info(
                        "LLM resolved %s -> %s (confidence=%.2f)",
                        entity.entity_id,
                        candidate.canonical_id,
                        result.confidence,
                    )
                    return candidate
            except Exception:
                logger.exception(
                    "LLM resolution failed for %s", entity.entity_id
                )

        return None
