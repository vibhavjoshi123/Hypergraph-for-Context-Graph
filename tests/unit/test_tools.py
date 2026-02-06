"""Tests for agent hypergraph tools."""

import pytest

from src.agents.tools import HypergraphTools
from src.models.hyperedges import Hyperedge, RoleAssignment
from src.typedb.traversal import HypergraphTraversal


class MockClient:
    """Mock TypeDB client for testing tools."""

    is_connected = False

    async def query(self, _):
        return []

    async def write(self, _):
        pass


class TestHypergraphTools:
    @pytest.fixture
    def sample_hyperedges(self):
        return [
            Hyperedge(
                hyperedge_id="he_1",
                participants=[
                    RoleAssignment(entity_id="a", role="p"),
                    RoleAssignment(entity_id="b", role="p"),
                    RoleAssignment(entity_id="c", role="p"),
                ],
            ),
            Hyperedge(
                hyperedge_id="he_2",
                participants=[
                    RoleAssignment(entity_id="b", role="p"),
                    RoleAssignment(entity_id="c", role="p"),
                    RoleAssignment(entity_id="d", role="p"),
                ],
            ),
            Hyperedge(
                hyperedge_id="he_3",
                participants=[
                    RoleAssignment(entity_id="c", role="p"),
                    RoleAssignment(entity_id="d", role="p"),
                    RoleAssignment(entity_id="e", role="p"),
                ],
            ),
        ]

    @pytest.fixture
    def tools(self, sample_hyperedges):
        traversal = HypergraphTraversal(sample_hyperedges)
        return HypergraphTools(MockClient(), traversal=traversal)

    def test_load_hyperedges(self):
        tools = HypergraphTools(MockClient())
        he = Hyperedge(
            hyperedge_id="test",
            participants=[
                RoleAssignment(entity_id="x", role="p"),
                RoleAssignment(entity_id="y", role="p"),
            ],
        )
        tools.load_hyperedges([he])
        assert len(tools.traversal.hyperedges) == 1

    @pytest.mark.asyncio
    async def test_find_paths(self, tools):
        paths = await tools.find_paths("a", "e", intersection_size=2, k_paths=3)
        assert len(paths) >= 1
        assert paths[0].is_valid()

    @pytest.mark.asyncio
    async def test_find_paths_no_connection(self, tools):
        paths = await tools.find_paths("a", "nonexistent", intersection_size=2)
        assert paths == []

    @pytest.mark.asyncio
    async def test_get_s_connected_components(self, tools):
        components = await tools.get_s_connected_components(s=2)
        assert len(components) >= 1

    @pytest.mark.asyncio
    async def test_get_entity_context(self, tools):
        ctx = await tools.get_entity_context("b", depth=2, s=2)
        assert ctx["entity_id"] == "b"
        assert ctx["node_degree"] == 2

    @pytest.mark.asyncio
    async def test_find_entity(self, tools):
        # With mock client, returns empty
        results = await tools.find_entity("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_hyperedges(self, tools):
        results = await tools.get_hyperedges("entity_1")
        assert results == []
