"""Tests for hypergraph traversal algorithms.

Tests BFS, Yen's K-shortest paths, s-adjacency, and connected
component analysis on in-memory hypergraph structures.
"""

import pytest

from src.models.hyperedges import Hyperedge, RoleAssignment
from src.typedb.traversal import HypergraphTraversal


def make_hyperedge(hid: str, entity_ids: list[str]) -> Hyperedge:
    """Helper to create a hyperedge with the given entity IDs."""
    return Hyperedge(
        hyperedge_id=hid,
        participants=[
            RoleAssignment(entity_id=eid, role="participant")
            for eid in entity_ids
        ],
    )


@pytest.fixture
def linear_graph():
    """A linear chain of hyperedges: h0 - h1 - h2 - h3.

    Each pair shares 2 entities (IS=2).
    h0: {a, b, c}
    h1: {b, c, d}
    h2: {c, d, e}
    h3: {d, e, f}
    """
    t = HypergraphTraversal()
    t.add_hyperedges([
        make_hyperedge("h0", ["a", "b", "c"]),
        make_hyperedge("h1", ["b", "c", "d"]),
        make_hyperedge("h2", ["c", "d", "e"]),
        make_hyperedge("h3", ["d", "e", "f"]),
    ])
    return t


@pytest.fixture
def branching_graph():
    """A branching graph:
    h0: {a, b, c}
    h1: {b, c, d}  (connected to h0 via IS=2)
    h2: {b, c, e}  (connected to h0 via IS=2)
    h3: {d, e, f}  (connected to h1 via IS=1, h2 via IS=1 -- below threshold)
    h4: {x, y, z}  (disconnected)
    """
    t = HypergraphTraversal()
    t.add_hyperedges([
        make_hyperedge("h0", ["a", "b", "c"]),
        make_hyperedge("h1", ["b", "c", "d"]),
        make_hyperedge("h2", ["b", "c", "e"]),
        make_hyperedge("h3", ["d", "e", "f"]),
        make_hyperedge("h4", ["x", "y", "z"]),
    ])
    return t


class TestSAdjacency:
    def test_neighbors_s2(self, linear_graph: HypergraphTraversal):
        neighbors = linear_graph.get_s_neighbors(0, s=2)
        assert 1 in neighbors
        # h0 shares {c} with h2, but only 1 entity, so not s=2 adjacent
        # Actually h0={a,b,c}, h2={c,d,e}, IS=1, not s=2 adjacent
        assert 2 not in neighbors

    def test_neighbors_s1(self, linear_graph: HypergraphTraversal):
        neighbors = linear_graph.get_s_neighbors(0, s=1)
        assert 1 in neighbors
        assert 2 in neighbors  # h0 and h2 share {c}

    def test_adjacency_matrix(self, linear_graph: HypergraphTraversal):
        adj = linear_graph.build_s_adjacency_matrix(s=2)
        assert 1 in adj[0]
        assert 0 in adj[1]
        assert 2 in adj[1]


class TestBFS:
    def test_bfs_shortest_path(self, linear_graph: HypergraphTraversal):
        path = linear_graph.bfs(0, target_idx=3, s=2)
        assert path is not None
        assert path[0] == 0
        assert path[-1] == 3

    def test_bfs_no_path(self, branching_graph: HypergraphTraversal):
        # h4 is disconnected
        path = branching_graph.bfs(0, target_idx=4, s=2)
        assert path is None

    def test_bfs_connected_component(self, branching_graph: HypergraphTraversal):
        component = branching_graph.bfs(0, target_idx=None, s=2)
        assert component is not None
        assert 0 in component
        assert 1 in component
        assert 2 in component
        assert 4 not in component

    def test_bfs_max_depth(self, linear_graph: HypergraphTraversal):
        # With max_depth=1, can only reach immediate neighbors
        path = linear_graph.bfs(0, target_idx=3, s=2, max_depth=1)
        assert path is None


class TestYenKShortestPaths:
    def test_single_path(self, linear_graph: HypergraphTraversal):
        paths = linear_graph.yen_k_shortest_paths(0, 3, k=1, s=2)
        assert len(paths) == 1
        assert paths[0][0] == 0
        assert paths[0][-1] == 3

    def test_multiple_paths(self, branching_graph: HypergraphTraversal):
        # h0 -> h1 and h0 -> h2 both have IS=2 with h0
        # h1 and h2 share {b, c} so they're s=2 adjacent
        paths = branching_graph.yen_k_shortest_paths(0, 2, k=3, s=2)
        assert len(paths) >= 1
        assert paths[0][0] == 0
        assert paths[0][-1] == 2

    def test_no_path(self, branching_graph: HypergraphTraversal):
        paths = branching_graph.yen_k_shortest_paths(0, 4, k=3, s=2)
        assert len(paths) == 0


class TestConnectedComponents:
    def test_components(self, branching_graph: HypergraphTraversal):
        components = branching_graph.find_s_connected_components(s=2)
        # h4 is disconnected, so we should have at least 2 components
        assert len(components) >= 2
        # Find the component containing h4 (index 4)
        h4_component = [c for c in components if 4 in c]
        assert len(h4_component) == 1
        assert h4_component[0] == [4]

    def test_single_component(self, linear_graph: HypergraphTraversal):
        components = linear_graph.find_s_connected_components(s=2)
        assert len(components) == 1
        assert len(components[0]) == 4


class TestTopologyMetrics:
    def test_node_degree(self, linear_graph: HypergraphTraversal):
        # entity 'c' appears in h0, h1, h2 => degree 3
        assert linear_graph.node_degree("c") == 3
        # entity 'a' appears in h0 only => degree 1
        assert linear_graph.node_degree("a") == 1

    def test_hub_nodes(self, linear_graph: HypergraphTraversal):
        hubs = linear_graph.hub_nodes(min_degree=3)
        hub_ids = [h[0] for h in hubs]
        assert "c" in hub_ids
        assert "d" in hub_ids

    def test_average_hyperedge_size(self, linear_graph: HypergraphTraversal):
        avg = linear_graph.average_hyperedge_size()
        assert avg == 3.0  # all hyperedges have 3 entities

    def test_empty_graph(self):
        t = HypergraphTraversal()
        assert t.average_hyperedge_size() == 0.0
        assert t.hub_nodes() == []


class TestPathConversion:
    def test_indices_to_path(self, linear_graph: HypergraphTraversal):
        path = linear_graph.indices_to_path([0, 1, 2])
        assert path.length == 3
        assert path.is_valid()

    def test_path_validation(self, linear_graph: HypergraphTraversal):
        # Valid path: h0 -> h1 -> h2
        path = linear_graph.indices_to_path([0, 1, 2], intersection_size=2)
        assert path.is_valid()

        # Invalid path: h0 -> h3 (not s=2 adjacent)
        path = linear_graph.indices_to_path([0, 3], intersection_size=2)
        assert not path.is_valid()
