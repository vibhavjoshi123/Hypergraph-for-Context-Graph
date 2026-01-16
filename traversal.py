"""
Enterprise Hypergraph Traversal

Implements graph traversal algorithms for the enterprise context graph.
Based on Section 4.4 "Graph Traversal Tools" from Stewart & Buehler.

Key algorithms:
1. BFS with intersection constraints (IS parameter)
2. Yen-style K-shortest paths
3. Node-based inverted index for efficient lookup
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass
import heapq

from models import (
    DecisionEvent, EnterpriseHypergraph, HypergraphPath,
    PathConstraint, AgentQuery, AgentResponse, ContextType
)


@dataclass
class TraversalState:
    """State during BFS traversal"""
    current_edge_id: str
    path: List[str]  # Edge IDs
    visited_edges: Set[str]
    total_intersection_size: int


class HypergraphIndex:
    """
    Inverted index for efficient hypergraph traversal.
    
    From paper: "The traversal algorithm begins by constructing an inverted 
    index that maps each node to the hyperedges in which it appears."
    """
    
    def __init__(self, hypergraph: EnterpriseHypergraph):
        self.hypergraph = hypergraph
        self.events_by_id: Dict[str, DecisionEvent] = {}
        self.node_to_edges: Dict[str, Set[str]] = defaultdict(set)
        self.edge_to_nodes: Dict[str, Set[str]] = {}
        
        self._build_index()
        
    def _build_index(self):
        """Build the inverted index"""
        for event in self.hypergraph.events:
            self.events_by_id[event.id] = event
            nodes = set(event.participants)
            self.edge_to_nodes[event.id] = nodes
            
            for node in nodes:
                self.node_to_edges[node].add(event.id)
                
    def get_edges_containing(self, node: str) -> Set[str]:
        """Get all edges containing a node"""
        return self.node_to_edges.get(node, set())
        
    def get_nodes_in_edge(self, edge_id: str) -> Set[str]:
        """Get all nodes in an edge"""
        return self.edge_to_nodes.get(edge_id, set())
        
    def get_edge_intersection(self, edge1_id: str, edge2_id: str) -> Set[str]:
        """Get intersection of two edges"""
        nodes1 = self.get_nodes_in_edge(edge1_id)
        nodes2 = self.get_nodes_in_edge(edge2_id)
        return nodes1 & nodes2
        
    def find_edges_with_node(self, node: str) -> List[DecisionEvent]:
        """Find all events containing a specific node"""
        edge_ids = self.get_edges_containing(node)
        return [self.events_by_id[eid] for eid in edge_ids if eid in self.events_by_id]


class HypergraphTraverser:
    """
    Traverses the enterprise hypergraph to find paths between concepts.
    
    Implements the BFS algorithm from the paper with node intersection
    constraints (IS) and Yen-style K-shortest paths.
    """
    
    def __init__(self, hypergraph: EnterpriseHypergraph):
        self.hypergraph = hypergraph
        self.index = HypergraphIndex(hypergraph)
        
    def find_shortest_path(
        self,
        start_node: str,
        end_node: str,
        constraints: PathConstraint
    ) -> Optional[HypergraphPath]:
        """
        Find shortest hypergraph path between two nodes.
        
        Uses BFS with intersection constraint: adjacent hyperedges must
        share at least IS nodes.
        """
        # Get starting edges (containing start_node)
        start_edges = self.index.get_edges_containing(start_node)
        if not start_edges:
            return None
            
        # Get ending edges (containing end_node)
        end_edges = self.index.get_edges_containing(end_node)
        if not end_edges:
            return None
            
        # BFS
        queue = deque()
        visited = set()
        
        # Initialize with all starting edges
        for edge_id in start_edges:
            state = TraversalState(
                current_edge_id=edge_id,
                path=[edge_id],
                visited_edges={edge_id},
                total_intersection_size=0
            )
            queue.append(state)
            
        while queue:
            state = queue.popleft()
            
            # Check if we've reached an ending edge
            if state.current_edge_id in end_edges:
                return self._build_path_result(
                    start_node, end_node, state.path
                )
                
            # Check path length constraint
            if len(state.path) >= constraints.max_path_length:
                continue
                
            # Get current edge's nodes
            current_nodes = self.index.get_nodes_in_edge(state.current_edge_id)
            
            # Find adjacent edges (sharing at least IS nodes)
            for node in current_nodes:
                for next_edge_id in self.index.get_edges_containing(node):
                    if next_edge_id in state.visited_edges:
                        continue
                        
                    # Check intersection constraint
                    intersection = self.index.get_edge_intersection(
                        state.current_edge_id, next_edge_id
                    )
                    
                    if len(intersection) >= constraints.intersection_size:
                        new_state = TraversalState(
                            current_edge_id=next_edge_id,
                            path=state.path + [next_edge_id],
                            visited_edges=state.visited_edges | {next_edge_id},
                            total_intersection_size=state.total_intersection_size + len(intersection)
                        )
                        queue.append(new_state)
                        
        return None  # No path found
        
    def find_k_shortest_paths(
        self,
        start_node: str,
        end_node: str,
        constraints: PathConstraint
    ) -> List[HypergraphPath]:
        """
        Find K shortest paths using Yen-style algorithm.
        
        From paper: "A Yen-style k-shortest path strategy then identifies 
        multiple alternative minimal-length hyperpaths (K1, K2), enabling 
        richer reasoning substrates."
        """
        k = constraints.k_paths
        paths = []
        candidates = []  # Min-heap of (path_length, path)
        
        # Find first shortest path
        first_path = self.find_shortest_path(start_node, end_node, constraints)
        if first_path is None:
            return []
            
        paths.append(first_path)
        
        # Find additional paths
        for i in range(1, k):
            # For each edge in the previous path
            prev_path = paths[-1]
            
            for j in range(len(prev_path.hyperedges) - 1):
                # Create a modified graph excluding this edge transition
                spur_node = self._get_spur_node(prev_path, j)
                if spur_node is None:
                    continue
                    
                # Find path from spur to end avoiding used edges
                root_path = prev_path.hyperedges[:j+1]
                excluded_edges = set(root_path)
                
                spur_path = self._find_path_excluding(
                    spur_node, end_node, constraints, excluded_edges
                )
                
                if spur_path:
                    # Combine root and spur paths
                    combined = root_path + spur_path.hyperedges
                    full_path = self._build_path_result(
                        start_node, end_node, combined
                    )
                    
                    if full_path and full_path not in paths:
                        heapq.heappush(
                            candidates,
                            (full_path.path_length, full_path)
                        )
                        
            # Add best candidate to paths
            while candidates:
                _, best = heapq.heappop(candidates)
                if best not in paths:
                    paths.append(best)
                    break
                    
            if len(paths) >= k:
                break
                
        return paths[:k]
        
    def _get_spur_node(self, path: HypergraphPath, index: int) -> Optional[str]:
        """Get the node at the intersection point in the path"""
        if index >= len(path.intersection_nodes):
            return None
        intersections = path.intersection_nodes[index]
        return intersections[0] if intersections else None
        
    def _find_path_excluding(
        self,
        start_node: str,
        end_node: str,
        constraints: PathConstraint,
        excluded_edges: Set[str]
    ) -> Optional[HypergraphPath]:
        """Find path excluding certain edges"""
        # Modified BFS excluding edges
        start_edges = self.index.get_edges_containing(start_node) - excluded_edges
        if not start_edges:
            return None
            
        end_edges = self.index.get_edges_containing(end_node)
        if not end_edges:
            return None
            
        queue = deque()
        
        for edge_id in start_edges:
            state = TraversalState(
                current_edge_id=edge_id,
                path=[edge_id],
                visited_edges={edge_id} | excluded_edges,
                total_intersection_size=0
            )
            queue.append(state)
            
        while queue:
            state = queue.popleft()
            
            if state.current_edge_id in end_edges:
                return self._build_path_result(
                    start_node, end_node, state.path
                )
                
            if len(state.path) >= constraints.max_path_length:
                continue
                
            current_nodes = self.index.get_nodes_in_edge(state.current_edge_id)
            
            for node in current_nodes:
                for next_edge_id in self.index.get_edges_containing(node):
                    if next_edge_id in state.visited_edges:
                        continue
                        
                    intersection = self.index.get_edge_intersection(
                        state.current_edge_id, next_edge_id
                    )
                    
                    if len(intersection) >= constraints.intersection_size:
                        new_state = TraversalState(
                            current_edge_id=next_edge_id,
                            path=state.path + [next_edge_id],
                            visited_edges=state.visited_edges | {next_edge_id},
                            total_intersection_size=state.total_intersection_size + len(intersection)
                        )
                        queue.append(new_state)
                        
        return None
        
    def _build_path_result(
        self,
        start_node: str,
        end_node: str,
        edge_ids: List[str]
    ) -> HypergraphPath:
        """Build a HypergraphPath result from edge IDs"""
        intersection_nodes = []
        total_intersection = 0
        
        for i in range(len(edge_ids) - 1):
            intersection = list(self.index.get_edge_intersection(
                edge_ids[i], edge_ids[i+1]
            ))
            intersection_nodes.append(intersection)
            total_intersection += len(intersection)
            
        return HypergraphPath(
            path_id=f"path_{hash(tuple(edge_ids))}",
            start_node=start_node,
            end_node=end_node,
            hyperedges=edge_ids,
            intersection_nodes=intersection_nodes,
            path_length=len(edge_ids),
            total_intersection_size=total_intersection
        )


class PathExplainer:
    """
    Generates natural language explanations for hypergraph paths.
    
    Converts structural paths to mechanistic explanations for agents.
    """
    
    def __init__(self, index: HypergraphIndex):
        self.index = index
        
    def explain_path(self, path: HypergraphPath) -> str:
        """Generate explanation for a path"""
        explanations = []
        
        for i, edge_id in enumerate(path.hyperedges):
            event = self.index.events_by_id.get(edge_id)
            if event:
                step = f"Step {i+1}: {event.decision_type} - {event.relation}"
                if event.participants:
                    step += f" (involving: {', '.join(event.participants[:3])})"
                explanations.append(step)
                
                # Add intersection context
                if i < len(path.intersection_nodes) and path.intersection_nodes[i]:
                    explanations.append(
                        f"  → Connected via: {', '.join(path.intersection_nodes[i])}"
                    )
                    
        return "\n".join(explanations)
        
    def to_natural_language_statements(
        self,
        path: HypergraphPath
    ) -> List[str]:
        """
        Convert path to natural language statements for agent context.
        
        From paper: "The extracted hyperedge sequence is translated into 
        natural-language statements by consulting a metadata dataframe."
        """
        statements = []
        
        for edge_id in path.hyperedges:
            event = self.index.events_by_id.get(edge_id)
            if event:
                # Format: "source - relation - target"
                if len(event.participants) >= 2:
                    stmt = f"{event.participants[0]} {event.relation} {event.participants[1]}"
                else:
                    stmt = f"{event.participants[0] if event.participants else 'unknown'} - {event.relation}"
                    
                if event.rationale:
                    stmt += f" (reason: {event.rationale})"
                    
                statements.append(stmt)
                
        return statements


class ContextGraphQueryEngine:
    """
    Query engine for the enterprise context graph.
    
    Handles agent queries, finds relevant paths, and synthesizes context.
    """
    
    def __init__(self, hypergraph: EnterpriseHypergraph):
        self.hypergraph = hypergraph
        self.traverser = HypergraphTraverser(hypergraph)
        self.explainer = PathExplainer(self.traverser.index)
        
    def query(self, agent_query: AgentQuery) -> AgentResponse:
        """
        Process an agent query and return relevant context.
        
        This is the main interface for agents to query the context graph.
        """
        all_paths = []
        
        # Find paths between all start/end concept pairs
        for start in agent_query.start_concepts:
            for end in agent_query.end_concepts:
                paths = self.traverser.find_k_shortest_paths(
                    start, end, agent_query.constraints
                )
                all_paths.extend(paths)
                
        # Generate explanations
        for path in all_paths:
            path.explanation = self.explainer.explain_path(path)
            
        # Collect context from paths
        operational_context = self._extract_operational_context(all_paths)
        analytical_context = self._extract_analytical_context(all_paths)
        
        # Generate summary
        summary = self._generate_context_summary(
            agent_query, all_paths, operational_context, analytical_context
        )
        
        return AgentResponse(
            query_id=agent_query.query_id,
            paths=all_paths,
            operational_context=operational_context,
            analytical_context=analytical_context,
            context_summary=summary,
            sources_used=self._get_sources_from_paths(all_paths),
            confidence_score=self._calculate_confidence(all_paths)
        )
        
    def _extract_operational_context(
        self,
        paths: List[HypergraphPath]
    ) -> List[Dict[str, Any]]:
        """Extract operational context (SOPs, policies) from paths"""
        context = []
        seen = set()
        
        for path in paths:
            for edge_id in path.hyperedges:
                event = self.traverser.index.events_by_id.get(edge_id)
                if event:
                    for ctx in event.operational_context:
                        if ctx not in seen:
                            context.append({
                                "id": ctx,
                                "type": "operational",
                                "source_event": edge_id
                            })
                            seen.add(ctx)
                            
        return context
        
    def _extract_analytical_context(
        self,
        paths: List[HypergraphPath]
    ) -> List[Dict[str, Any]]:
        """Extract analytical context (metrics, definitions) from paths"""
        context = []
        seen = set()
        
        for path in paths:
            for edge_id in path.hyperedges:
                event = self.traverser.index.events_by_id.get(edge_id)
                if event:
                    for ctx in event.analytical_context:
                        if ctx not in seen:
                            context.append({
                                "id": ctx,
                                "type": "analytical",
                                "source_event": edge_id
                            })
                            seen.add(ctx)
                            
        return context
        
    def _generate_context_summary(
        self,
        query: AgentQuery,
        paths: List[HypergraphPath],
        operational: List[Dict],
        analytical: List[Dict]
    ) -> str:
        """Generate a summary of the retrieved context"""
        summary_parts = []
        
        summary_parts.append(f"Query: {query.query_text}")
        summary_parts.append(f"Found {len(paths)} paths connecting concepts.")
        
        if paths:
            # Summarize key intersections
            all_intersections = set()
            for path in paths:
                for intersection in path.intersection_nodes:
                    all_intersections.update(intersection)
                    
            if all_intersections:
                summary_parts.append(
                    f"Key bridging entities: {', '.join(list(all_intersections)[:5])}"
                )
                
        if operational:
            summary_parts.append(
                f"Relevant policies/SOPs: {len(operational)} found"
            )
            
        if analytical:
            summary_parts.append(
                f"Relevant metrics/definitions: {len(analytical)} found"
            )
            
        return "\n".join(summary_parts)
        
    def _get_sources_from_paths(self, paths: List[HypergraphPath]) -> List[str]:
        """Get all data sources referenced in paths"""
        sources = set()
        for path in paths:
            for edge_id in path.hyperedges:
                event = self.traverser.index.events_by_id.get(edge_id)
                if event:
                    for src in event.source_systems:
                        sources.add(src.value)
        return list(sources)
        
    def _calculate_confidence(self, paths: List[HypergraphPath]) -> float:
        """Calculate overall confidence based on path quality"""
        if not paths:
            return 0.0
            
        # Factors: path length, intersection sizes, number of paths
        scores = []
        for path in paths:
            # Shorter paths = higher confidence
            length_score = 1.0 / (1.0 + path.path_length * 0.1)
            # More intersections = higher confidence
            intersection_score = min(1.0, path.total_intersection_size / 10.0)
            scores.append((length_score + intersection_score) / 2)
            
        return sum(scores) / len(scores)


def demo_graph_traversal():
    """Demonstrate graph traversal capabilities"""
    from hypergraph_builder import demo_build_enterprise_hypergraph
    
    # Build the hypergraph
    builder, hypergraph = demo_build_enterprise_hypergraph()
    
    # Create query engine
    engine = ContextGraphQueryEngine(hypergraph)
    
    # Example query: "Why was Acme Corp given a discount?"
    query = AgentQuery(
        query_id="q_001",
        agent_type="sales_agent",
        start_concepts=["cust_acme"],
        end_concepts=["vp_sales"],
        query_text="Why was Acme Corp given a 20% discount?",
        constraints=PathConstraint(
            intersection_size=1,
            k_paths=3
        )
    )
    
    response = engine.query(query)
    
    print("\n=== Query Response ===")
    print(f"Query: {query.query_text}")
    print(f"\nContext Summary:\n{response.context_summary}")
    
    print(f"\n=== Paths Found: {len(response.paths)} ===")
    for i, path in enumerate(response.paths):
        print(f"\nPath {i+1}:")
        print(path.explanation)
        
    print(f"\n=== Operational Context ===")
    for ctx in response.operational_context:
        print(f"  - {ctx['id']} (from {ctx['source_event']})")
        
    print(f"\n=== Analytical Context ===")
    for ctx in response.analytical_context:
        print(f"  - {ctx['id']} (from {ctx['source_event']})")
        
    return engine, response


if __name__ == "__main__":
    demo_graph_traversal()
