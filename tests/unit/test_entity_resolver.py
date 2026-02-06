"""Tests for entity resolution."""

import pytest

from src.extraction.entity_resolver import EntityResolver, ResolvedEntity
from src.extraction.pipeline import ExtractedEntity


class TestEntityResolver:
    @pytest.fixture
    def resolver(self):
        return EntityResolver()

    @pytest.mark.asyncio
    async def test_resolve_new_entity(self, resolver):
        entity = ExtractedEntity(
            entity_id="cust_001",
            entity_name="Acme Corp",
            entity_type="customer",
        )
        resolved = await resolver.resolve(entity, "salesforce")
        assert resolved.canonical_id == "cust_001"
        assert resolved.canonical_name == "Acme Corp"
        assert resolved.source_ids["salesforce"] == "cust_001"

    @pytest.mark.asyncio
    async def test_resolve_same_entity_by_name(self, resolver):
        entity1 = ExtractedEntity(
            entity_id="sf_001",
            entity_name="Acme Corp",
            entity_type="customer",
        )
        entity2 = ExtractedEntity(
            entity_id="zd_001",
            entity_name="Acme Corp",
            entity_type="customer",
        )
        resolved1 = await resolver.resolve(entity1, "salesforce")
        resolved2 = await resolver.resolve(entity2, "zendesk")

        assert resolved1.canonical_id == resolved2.canonical_id
        assert "salesforce" in resolved2.source_ids
        assert "zendesk" in resolved2.source_ids

    @pytest.mark.asyncio
    async def test_resolve_different_entities(self, resolver):
        entity1 = ExtractedEntity(
            entity_id="cust_001",
            entity_name="Acme Corp",
            entity_type="customer",
        )
        entity2 = ExtractedEntity(
            entity_id="cust_002",
            entity_name="Globex Inc",
            entity_type="customer",
        )
        resolved1 = await resolver.resolve(entity1, "salesforce")
        resolved2 = await resolver.resolve(entity2, "salesforce")

        assert resolved1.canonical_id != resolved2.canonical_id

    @pytest.mark.asyncio
    async def test_resolve_batch(self, resolver):
        entities = [
            ExtractedEntity(
                entity_id="e1", entity_name="Entity One", entity_type="customer"
            ),
            ExtractedEntity(
                entity_id="e2", entity_name="Entity Two", entity_type="deal"
            ),
        ]
        results = await resolver.resolve_batch(entities, "test")
        assert len(results) == 2

    def test_known_entities(self):
        resolver = EntityResolver()
        assert resolver.known_entities == {}


class TestResolvedEntity:
    def test_creation(self):
        entity = ResolvedEntity(
            canonical_id="c1",
            canonical_name="Acme",
            entity_type="customer",
            source_ids={"salesforce": "sf_001", "zendesk": "zd_001"},
        )
        assert entity.canonical_id == "c1"
        assert len(entity.source_ids) == 2
