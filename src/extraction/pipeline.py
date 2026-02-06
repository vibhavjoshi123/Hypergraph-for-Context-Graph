"""LLM-powered entity extraction pipeline.

Processes RawRecord objects from enterprise connectors, uses LLMs to
extract entities and n-ary relationships, and produces structured
output ready for insertion into the TypeDB hypergraph.

From ARCHITECTURE_PLAN.md Section 3.4.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from src.connectors.base import RawRecord
from src.llm.base import BaseLLMConnector
from src.llm.prompts.extraction import (
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_EXTRACTION_SYSTEM,
)

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    """An entity extracted by the LLM from a raw record."""

    entity_id: str
    entity_name: str
    entity_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExtractedRelationship(BaseModel):
    """An n-ary relationship extracted by the LLM."""

    relation_type: str
    participants: list[dict[str, str]] = Field(
        ..., description="List of {entity_id, role} dicts"
    )
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Result of entity extraction from a single record."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    source_record_id: str | None = None
    source_system: str | None = None


class EntityExtractionPipeline:
    """Pipeline for extracting entities and relationships from raw records.

    Uses LLM-powered extraction to identify entities and their n-ary
    relationships, then normalizes them for insertion into the hypergraph.
    """

    def __init__(self, llm: BaseLLMConnector) -> None:
        self.llm = llm

    async def extract(self, record: RawRecord) -> ExtractionResult:
        """Extract entities and relationships from a raw record.

        Args:
            record: Raw record from an enterprise data connector.

        Returns:
            ExtractionResult with identified entities and relationships.
        """
        prompt = ENTITY_EXTRACTION_PROMPT.format(
            source_system=record.source_system,
            record_type=record.record_type,
            data=json.dumps(record.data, indent=2, default=str),
        )

        try:
            result = await self.llm.complete_structured(
                prompt=prompt,
                output_schema=ExtractionResult,
                system_prompt=ENTITY_EXTRACTION_SYSTEM,
            )
            result.source_record_id = record.record_id
            result.source_system = record.source_system
            return result
        except Exception:
            logger.exception(
                "Extraction failed for record %s from %s",
                record.record_id,
                record.source_system,
            )
            return ExtractionResult(
                source_record_id=record.record_id,
                source_system=record.source_system,
            )

    async def extract_batch(self, records: list[RawRecord]) -> list[ExtractionResult]:
        """Extract entities from multiple records."""
        results: list[ExtractionResult] = []
        for record in records:
            result = await self.extract(record)
            results.append(result)
        return results
