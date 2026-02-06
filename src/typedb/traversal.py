"""Hypergraph traversal algorithms.

Implements BFS and Yen's K-shortest paths with intersection size (IS)
constraints on the hypergraph, following the MIT paper's methodology.

Key algorithms:
- BFS with IS >= s constraint for s-connected component discovery
- Yen's K-shortest s-paths for finding multiple decision traces
- s-connected component analysis for stability assessment

From the Chemical Reaction Networks PDF:
- Paths = reaction mechanisms / metabolic pathways / decision traces
- IS constraint = conservation law analogue (mass conservation -> shared entities)
"""

from __future__ import annotations

import heapq
import logging
from collections import defaultdict, deque

from src.models.hyperedges import Hyperedge, HypergraphPath

logger = logging.getLogger(__name__)


class HypergraphTraversal:
    """Graph traversal algorithms over the in-memory hypergraph.

    Operates on collections of Hyperedge objects. For TypeDB-backed
    traversal, the TypeDB client issues TypeQL queries directly.
    This class provides algorithmic support for path-finding over
    hyperedge sets retrieved from the database.
    """

    def __init__(self, hyperedges: list[Hyperedge] | None = None) -> None:
        self._hyperedges: list[Hyperedge] = hyperedges or []
        # Adjacency index: entity_id -> list of hyperedge indices
        self._entity_index: dict[str, list[int]] = defaultdict(list)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the entity-to-hyperedge index."""
        self._entity_index.clear()
        for idx, he in enumerate(self._hyperedges):
            for eid in he.entity_ids:
                self._entity_index[eid].append(idx)

    def add_hyperedge(self, hyperedge: Hyperedge) -> None:
        """Add a hyperedge to the traversal set."""
        idx = len(self._hyperedges)
        self._hyperedges.append(hyperedge)
        for eid in hyperedge.entity_ids:
            self._entity_index[eid].append(idx)

    def add_hyperedges(self, hyperedges: list[Hyperedge]) -> None:
        """Add multiple hyperedges."""
        for he in hyperedges:
            self.add_hyperedge(he)

    @property
    def hyperedges(self) -> list[Hyperedge]:
        return list(self._hyperedges)

    # ── s-Adjacency ────────────────────────────────────────────────────

    def get_s_neighbors(self, hyperedge_idx: int, s: int = 2) -> list[int]:
        """Find all hyperedges that are s-adjacent to the given one.

        Two hyperedges are s-adjacent iff they share >= s entities.
        IS >= 2 reduces noise by 87% (MIT paper Table 4).
        """
        target = self._hyperedges[hyperedge_idx]
        neighbors: list[int] = []
        seen: set[int] = {hyperedge_idx}

        for eid in target.entity_ids:
            for other_idx in self._entity_index[eid]:
                if other_idx in seen:
                    continue
                seen.add(other_idx)
                if target.is_s_adjacent(self._hyperedges[other_idx], s):
                    neighbors.append(other_idx)
        return neighbors

    def build_s_adjacency_matrix(self, s: int = 2) -> dict[int, list[int]]:
        """Build the full s-adjacency graph (line graph of the hypergraph).

        Returns adjacency list: hyperedge_idx -> [adjacent hyperedge indices].
        """
        adj: dict[int, list[int]] = {}
        for idx in range(len(self._hyperedges)):
            adj[idx] = self.get_s_neighbors(idx, s)
        return adj

    # ── BFS ────────────────────────────────────────────────────────────

    def bfs(
        self,
        start_idx: int,
        target_idx: int | None = None,
        s: int = 2,
        max_depth: int = 10,
    ) -> list[int] | None:
        """BFS over s-adjacent hyperedges.

        If target_idx is given, returns the shortest s-path from start to target.
        Otherwise, returns all reachable hyperedge indices (s-connected component).

        Args:
            start_idx: Starting hyperedge index.
            target_idx: Optional target hyperedge index.
            s: Minimum intersection size for adjacency.
            max_depth: Maximum path length to search.

        Returns:
            Path as list of hyperedge indices (if target given), or
            all reachable indices (if target is None).
        """
        visited: set[int] = {start_idx}
        parent: dict[int, int | None] = {start_idx: None}
        queue: deque[tuple[int, int]] = deque([(start_idx, 0)])

        while queue:
            current, depth = queue.popleft()

            if target_idx is not None and current == target_idx:
                # Reconstruct path
                path: list[int] = []
                node: int | None = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))

            if depth >= max_depth:
                continue

            for neighbor in self.get_s_neighbors(current, s):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append((neighbor, depth + 1))

        if target_idx is not None:
            return None  # No path found
        return list(visited)  # Return connected component

    # ── Yen's K-Shortest Paths ─────────────────────────────────────────

    def yen_k_shortest_paths(
        self,
        start_idx: int,
        target_idx: int,
        k: int = 3,
        s: int = 2,
        max_depth: int = 10,
    ) -> list[list[int]]:
        """Find K shortest s-paths using Yen's algorithm.

        From the MIT paper: finding multiple paths between concepts enables
        hypothesis generation by revealing different connection patterns.

        Args:
            start_idx: Starting hyperedge index.
            target_idx: Target hyperedge index.
            k: Number of shortest paths to find.
            s: Minimum intersection size for adjacency.
            max_depth: Maximum path length.

        Returns:
            List of paths (each path is a list of hyperedge indices).
        """
        # Find the first shortest path via BFS
        shortest = self.bfs(start_idx, target_idx, s, max_depth)
        if shortest is None:
            return []

        a_paths: list[list[int]] = [shortest]
        b_candidates: list[tuple[int, list[int]]] = []  # (cost, path)

        for k_i in range(1, k):
            if not a_paths:
                break

            prev_path = a_paths[k_i - 1]

            for spur_idx in range(len(prev_path) - 1):
                spur_node = prev_path[spur_idx]
                root_path = prev_path[: spur_idx + 1]

                # Edges to exclude: any edge used by existing paths
                # that share the same root
                excluded_edges: set[tuple[int, int]] = set()
                for path in a_paths:
                    if path[: spur_idx + 1] == root_path and spur_idx + 1 < len(path):
                        excluded_edges.add((path[spur_idx], path[spur_idx + 1]))

                excluded_nodes: set[int] = set(root_path[:-1])

                # BFS from spur_node to target, avoiding excluded edges/nodes
                spur_path = self._restricted_bfs(
                    spur_node, target_idx, s, max_depth - spur_idx,
                    excluded_edges, excluded_nodes,
                )

                if spur_path is not None:
                    total_path = root_path[:-1] + spur_path
                    cost = len(total_path)
                    if (cost, total_path) not in b_candidates:
                        heapq.heappush(b_candidates, (cost, total_path))

            if not b_candidates:
                break

            _, next_path = heapq.heappop(b_candidates)
            a_paths.append(next_path)

        return a_paths

    def _restricted_bfs(
        self,
        start_idx: int,
        target_idx: int,
        s: int,
        max_depth: int,
        excluded_edges: set[tuple[int, int]],
        excluded_nodes: set[int],
    ) -> list[int] | None:
        """BFS with excluded edges and nodes (used by Yen's algorithm)."""
        visited: set[int] = {start_idx} | excluded_nodes
        parent: dict[int, int | None] = {start_idx: None}
        queue: deque[tuple[int, int]] = deque([(start_idx, 0)])

        while queue:
            current, depth = queue.popleft()

            if current == target_idx:
                path: list[int] = []
                node: int | None = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))

            if depth >= max_depth:
                continue

            for neighbor in self.get_s_neighbors(current, s):
                if neighbor in visited:
                    continue
                if (current, neighbor) in excluded_edges:
                    continue
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append((neighbor, depth + 1))

        return None

    # ── s-Connected Components ─────────────────────────────────────────

    def find_s_connected_components(self, s: int = 2) -> list[list[int]]:
        """Find all s-connected components in the hypergraph.

        An s-connected component is a maximal set of hyperedges where
        every pair is connected by an s-walk (chain of s-adjacent hyperedges).

        From the MIT paper: components reveal clusters of related decisions
        that share sufficient context (entities) to form meaningful chains.
        """
        visited: set[int] = set()
        components: list[list[int]] = []

        for idx in range(len(self._hyperedges)):
            if idx in visited:
                continue
            component = self.bfs(idx, target_idx=None, s=s)
            if component:
                visited.update(component)
                components.append(sorted(component))

        return components

    # ── Path Conversion ────────────────────────────────────────────────

    def indices_to_path(
        self,
        indices: list[int],
        intersection_size: int = 2,
    ) -> HypergraphPath:
        """Convert a list of hyperedge indices to a HypergraphPath model."""
        return HypergraphPath(
            hyperedges=[self._hyperedges[i] for i in indices],
            intersection_size=intersection_size,
        )

    # ── Topology Metrics ───────────────────────────────────────────────

    def node_degree(self, entity_id: str) -> int:
        """How many hyperedges involve this entity (node degree)."""
        return len(self._entity_index.get(entity_id, []))

    def hub_nodes(self, min_degree: int = 5) -> list[tuple[str, int]]:
        """Find hub nodes (high-degree entities).

        From Chemical Reaction Networks PDF: hub molecules like ATP/NADH
        in metabolism; key customers, core policies in enterprise.
        """
        hubs: list[tuple[str, int]] = []
        for eid, indices in self._entity_index.items():
            if len(indices) >= min_degree:
                hubs.append((eid, len(indices)))
        return sorted(hubs, key=lambda x: x[1], reverse=True)

    def average_hyperedge_size(self) -> float:
        """Average cardinality of hyperedges."""
        if not self._hyperedges:
            return 0.0
        return sum(he.cardinality for he in self._hyperedges) / len(self._hyperedges)
