"""Tests for hyperedge builder."""

import pytest

from src.extraction.hyperedge_builder import RELATION_TYPE_MAP, HyperedgeBuilder
from src.extraction.pipeline import (
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
)
from src.models.hyperedges import RelationType


class TestRelationTypeMap:
    def test_all_relation_types_mapped(self):
        assert "decision-event" in RELATION_TYPE_MAP
        assert "escalation" in RELATION_TYPE_MAP
        assert "approval" in RELATION_TYPE_MAP
        assert RELATION_TYPE_MAP["decision-event"] == RelationType.DECISION


class TestHyperedgeBuilder:
    @pytest.fixture
    def builder(self):
        return HyperedgeBuilder()

    @pytest.mark.asyncio
    async def test_build_from_extraction(self, builder):
        result = ExtractionResult(
            entities=[
                ExtractedEntity(
                    entity_id="c1", entity_name="Acme", entity_type="customer"
                ),
                ExtractedEntity(
                    entity_id="e1", entity_name="VP Sales", entity_type="employee"
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    relation_type="decision-event",
                    participants=[
                        {"entity_id": "c1", "role": "involved-entity"},
                        {"entity_id": "e1", "role": "decision-maker"},
                    ],
                    attributes={"decision_type": "discount-approval"},
                ),
            ],
            source_system="salesforce",
        )
        hyperedges = await builder.build_from_extraction(result)
        assert len(hyperedges) == 1
        assert hyperedges[0].relation_type == RelationType.DECISION
        assert len(hyperedges[0].participants) == 2

    @pytest.mark.asyncio
    async def test_build_empty_result(self, builder):
        result = ExtractionResult(source_system="test")
        hyperedges = await builder.build_from_extraction(result)
        assert hyperedges == []

    @pytest.mark.asyncio
    async def test_build_context_hyperedge(self, builder):
        result = ExtractionResult(
            entities=[
                ExtractedEntity(
                    entity_id="a", entity_name="A", entity_type="customer"
                ),
                ExtractedEntity(
                    entity_id="b", entity_name="B", entity_type="deal"
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    relation_type="context-hyperedge",
                    participants=[
                        {"entity_id": "a", "role": "participant"},
                        {"entity_id": "b", "role": "participant"},
                    ],
                ),
            ],
            source_system="test",
        )
        hyperedges = await builder.build_from_extraction(result)
        assert len(hyperedges) == 1
        assert hyperedges[0].relation_type == RelationType.CONTEXT

    @pytest.mark.asyncio
    async def test_build_batch(self, builder):
        results = [
            ExtractionResult(
                entities=[
                    ExtractedEntity(
                        entity_id="x", entity_name="X", entity_type="customer"
                    ),
                    ExtractedEntity(
                        entity_id="y", entity_name="Y", entity_type="employee"
                    ),
                ],
                relationships=[
                    ExtractedRelationship(
                        relation_type="approval",
                        participants=[
                            {"entity_id": "x", "role": "requester"},
                            {"entity_id": "y", "role": "approver"},
                        ],
                    ),
                ],
                source_system="test",
            ),
        ]
        hyperedges = await builder.build_batch(results)
        assert len(hyperedges) == 1
