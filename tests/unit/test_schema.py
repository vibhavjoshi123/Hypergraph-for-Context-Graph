"""Tests for TypeDB schema definitions."""

from src.typedb.schema import SCHEMA_TYPEQL, SchemaManager


class TestSchemaManager:
    def test_schema_not_empty(self):
        mgr = SchemaManager()
        schema = mgr.get_schema()
        assert len(schema) > 100

    def test_schema_has_entities(self):
        mgr = SchemaManager()
        schema = mgr.get_schema()
        assert "entity customer" in schema
        assert "entity employee" in schema
        assert "entity deal" in schema
        assert "entity ticket" in schema
        assert "entity policy" in schema
        assert "entity metric" in schema

    def test_schema_has_relations(self):
        mgr = SchemaManager()
        schema = mgr.get_schema()
        assert "relation context-hyperedge" in schema
        assert "relation decision-event" in schema
        assert "relation precedent-chain" in schema
        assert "relation exception-override" in schema

    def test_schema_has_inference_rules(self):
        mgr = SchemaManager()
        schema = mgr.get_schema()
        assert "rule customer-at-risk" in schema

    def test_entity_types_list(self):
        mgr = SchemaManager()
        types = mgr.get_entity_types()
        assert "customer" in types
        assert "deal" in types
        assert len(types) == 6

    def test_relation_types_list(self):
        mgr = SchemaManager()
        types = mgr.get_relation_types()
        assert "decision-event" in types
        assert "precedent-chain" in types
        assert len(types) == 8

    def test_schema_has_2_morphism_support(self):
        """Verify nested relation support for 2-morphisms."""
        schema = SCHEMA_TYPEQL
        assert "plays precedent-chain:precedent-decision" in schema
        assert "plays precedent-chain:derived-decision" in schema
        assert "plays exception-override:base-decision" in schema
