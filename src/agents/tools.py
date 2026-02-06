"""Agent tools for interacting with the TypeDB hypergraph.

Provides a high-level tool interface that agents use to search entities,
find paths, and analyze the hypergraph structure.

From ARCHITECTURE_PLAN.md Section 4.2.
"""

from __future__ import annotations

import logging
from typing import Any

from src.models.hyperedges import Hyperedge, HypergraphPath
from src.typedb.client import TypeDBClient
from src.typedb.embeddings import EmbeddingStore
from src.typedb.operations import HypergraphOperations
from src.typedb.traversal import HypergraphTraversal

logger = logging.getLogger(__name__)


class HypergraphTools:
    """Tools for agents to interact with the hypergraph.

    Combines TypeDB operations, traversal algorithms, and embedding
    search into a unified tool interface for the agent system.
    """

    def __init__(
        self,
        client: TypeDBClient,
        traversal: HypergraphTraversal | None = None,
    ) -> None:
        self._client = client
        self._ops = HypergraphOperations(client)
        self._embeddings = EmbeddingStore(client)
        self._traversal = traversal or HypergraphTraversal()

    @property
    def traversal(self) -> HypergraphTraversal:
        """Access the underlying traversal engine."""
        return self._traversal

    async def find_entity(
        self,
        query: str,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for entities by name or semantic similarity.

        First tries exact name match via TypeQL, then falls back
        to embedding-based similarity search.
        """
        # Try TypeQL name search first
        type_clause = f"$e isa {entity_type}" if entity_type else "$e isa enterprise-entity"
        typeql = f"""
        match
            {type_clause}, has entity-name $name;
            $name contains "{query}";
        fetch $e: attribute;
        """
        results = await self._client.query(typeql)
        if results:
            return results

        # Fall back to entity-id search
        entity = await self._ops.get_entity(query)
        if entity:
            return [entity]

        return []

    async def get_hyperedges(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all hyperedges involving an entity."""
        return await self._ops.get_hyperedges_for_entity(entity_id)

    async def find_paths(
        self,
        start_id: str,
        end_id: str,
        intersection_size: int = 2,
        k_paths: int = 3,
    ) -> list[HypergraphPath]:
        """Find K shortest paths between two entities' hyperedges.

        Locates the hyperedges involving each entity, then uses
        Yen's K-shortest paths algorithm with IS constraints.
        """
        # Find hyperedge indices for start and end entities
        start_indices = self._find_entity_hyperedge_indices(start_id)
        end_indices = self._find_entity_hyperedge_indices(end_id)

        if not start_indices or not end_indices:
            return []

        all_paths: list[HypergraphPath] = []
        for s_idx in start_indices:
            for e_idx in end_indices:
                if s_idx == e_idx:
                    continue
                index_paths = self._traversal.yen_k_shortest_paths(
                    s_idx, e_idx, k=k_paths, s=intersection_size,
                )
                for idx_path in index_paths:
                    path = self._traversal.indices_to_path(
                        idx_path, intersection_size
                    )
                    all_paths.append(path)

        # Sort by path length and return top k
        all_paths.sort(key=lambda p: p.length)
        return all_paths[:k_paths]

    async def get_s_connected_components(
        self,
        s: int = 2,
    ) -> list[list[int]]:
        """Find s-connected components in the hypergraph."""
        return self._traversal.find_s_connected_components(s)

    async def get_entity_context(
        self,
        entity_id: str,
        depth: int = 2,
        s: int = 2,
    ) -> dict[str, Any]:
        """Get full context for an entity: hyperedges, neighbors, paths.

        Provides a comprehensive view of an entity's position in the
        hypergraph, useful for agents building reasoning context.
        """
        hyperedges = await self.get_hyperedges(entity_id)
        indices = self._find_entity_hyperedge_indices(entity_id)

        # BFS from each hyperedge to find connected context
        reachable: set[int] = set()
        for idx in indices:
            component = self._traversal.bfs(idx, s=s, max_depth=depth)
            if component:
                reachable.update(component)

        degree = self._traversal.node_degree(entity_id)

        return {
            "entity_id": entity_id,
            "hyperedge_count": len(hyperedges),
            "node_degree": degree,
            "reachable_hyperedges": len(reachable),
            "hyperedges": hyperedges,
        }

    async def semantic_search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search entities by embedding similarity."""
        return await self._embeddings.find_similar(
            query_embedding, top_k=top_k
        )

    def load_hyperedges(self, hyperedges: list[Hyperedge]) -> None:
        """Load hyperedges into the in-memory traversal engine."""
        self._traversal.add_hyperedges(hyperedges)
        logger.info(
            "Loaded %d hyperedges into traversal engine (total: %d)",
            len(hyperedges),
            len(self._traversal.hyperedges),
        )

    def _find_entity_hyperedge_indices(self, entity_id: str) -> list[int]:
        """Find hyperedge indices containing a given entity."""
        return self._traversal._entity_index.get(entity_id, [])
