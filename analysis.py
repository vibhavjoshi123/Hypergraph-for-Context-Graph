"""
Enterprise Hypergraph Analysis

Implements analysis techniques from Section 2.2 of Stewart & Buehler:
- Degree distribution analysis (Figure 5)
- Hub detection and analysis (Table 2)
- s-connected components (Table 4)
- Rich-club analysis (Table 3)

Enterprise-specific analytics:
- Decision pattern detection
- Anomaly identification (low-s components = areas of flux)
- Stability analysis (high-s components = established SOPs)
"""

import math
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

from models import (
    EnterpriseHypergraph, DecisionEvent, 
    ContextType, DataSource
)


@dataclass
class NodeStatistics:
    """Statistics for a single node"""
    node_id: str
    degree: int  # Number of hyperedges containing this node
    unique_neighbors: int  # Number of unique co-occurring nodes
    neighbor_density: float  # Density of ego network
    avg_edge_size: float  # Average size of edges containing this node
    top_cooccurring: List[Tuple[str, int]]  # Top co-occurring nodes


@dataclass
class HubAnalysis:
    """Analysis of hub nodes (Table 2 from paper)"""
    hubs: List[NodeStatistics]
    hub_integration_scores: Dict[str, int]  # Co-occurrences with other hubs
    rich_club_coefficients: Dict[int, float]  # Degree threshold -> coefficient


@dataclass 
class ComponentAnalysis:
    """Analysis of s-connected components (Table 4 from paper)"""
    s_value: int
    num_components: int
    largest_component_size: int
    top_component_sizes: List[int]
    component_members: List[Set[str]]  # Edge IDs in each component


class HypergraphAnalyzer:
    """
    Analyzes the structure of the enterprise hypergraph.
    
    From paper: "To study the structural behavior of the hypergraph more 
    efficiently, we can visualize and examine random subgraphs sampled 
    from the global network."
    """
    
    def __init__(self, hypergraph: EnterpriseHypergraph):
        self.hypergraph = hypergraph
        self._build_indices()
        
    def _build_indices(self):
        """Build analysis indices"""
        self.node_to_edges: Dict[str, Set[str]] = defaultdict(set)
        self.edge_to_nodes: Dict[str, Set[str]] = {}
        self.node_degree: Dict[str, int] = Counter()
        
        for event in self.hypergraph.events:
            nodes = set(event.participants)
            self.edge_to_nodes[event.id] = nodes
            
            for node in nodes:
                self.node_to_edges[node].add(event.id)
                self.node_degree[node] += 1
                
    def get_basic_statistics(self) -> Dict[str, Any]:
        """
        Get basic hypergraph statistics (Table 1 from paper).
        
        Enterprise interpretation:
        - Nodes = entities (customers, employees, deals, tickets)
        - Edges = decision events
        - Edge size = number of participants in decision
        """
        if not self.hypergraph.events:
            return {}
            
        edge_sizes = [len(e.participants) for e in self.hypergraph.events]
        node_degrees = list(self.node_degree.values())
        
        # Calculate overlap statistics
        overlap_counts = {1: 0, 2: 0, 3: 0}
        edges = list(self.edge_to_nodes.items())
        
        for i, (e1_id, e1_nodes) in enumerate(edges):
            for e2_id, e2_nodes in edges[i+1:]:
                overlap = len(e1_nodes & e2_nodes)
                if overlap >= 1:
                    overlap_counts[1] += 1
                if overlap >= 2:
                    overlap_counts[2] += 1
                if overlap >= 3:
                    overlap_counts[3] += 1
                    
        return {
            "num_nodes": len(self.node_degree),
            "num_edges": len(self.hypergraph.events),
            "avg_edge_size": sum(edge_sizes) / len(edge_sizes),
            "max_edge_size": max(edge_sizes),
            "min_edge_size": min(edge_sizes),
            "avg_node_degree": sum(node_degrees) / len(node_degrees),
            "max_node_degree": max(node_degrees),
            "pairs_overlap_1": overlap_counts[1],
            "pairs_overlap_2": overlap_counts[2],
            "pairs_overlap_3": overlap_counts[3]
        }
        
    def get_degree_distribution(self) -> Dict[int, int]:
        """
        Get node degree distribution (Figure 5 from paper).
        
        Enterprise interpretation:
        - High-degree nodes = frequently involved entities (key customers, 
          active employees, recurring issues)
        - Long tail = specialized or context-dependent entities
        """
        distribution = Counter()
        for degree in self.node_degree.values():
            distribution[degree] += 1
        return dict(sorted(distribution.items()))
        
    def fit_power_law(self) -> Tuple[float, float]:
        """
        Fit power law to degree distribution.
        
        From paper: "fitted power-law trend (y = 1.23, R² = 0.755)"
        
        Enterprise interpretation:
        - Scale-free structure indicates few "hub" entities
        - Most entities are peripheral with few connections
        """
        distribution = self.get_degree_distribution()
        
        # Log-log transformation
        log_degrees = []
        log_frequencies = []
        
        for degree, count in distribution.items():
            if degree > 0 and count > 0:
                log_degrees.append(math.log10(degree))
                log_frequencies.append(math.log10(count))
                
        if len(log_degrees) < 2:
            return 0.0, 0.0
            
        # Simple linear regression
        n = len(log_degrees)
        sum_x = sum(log_degrees)
        sum_y = sum(log_frequencies)
        sum_xy = sum(x * y for x, y in zip(log_degrees, log_frequencies))
        sum_xx = sum(x * x for x in log_degrees)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x + 1e-10)
        intercept = (sum_y - slope * sum_x) / n
        
        # R-squared
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for y in log_frequencies)
        ss_res = sum((y - (slope * x + intercept)) ** 2 
                    for x, y in zip(log_degrees, log_frequencies))
        r_squared = 1 - (ss_res / (ss_tot + 1e-10))
        
        return abs(slope), r_squared
        
    def identify_hubs(self, top_k: int = 20) -> HubAnalysis:
        """
        Identify and analyze hub nodes (Table 2 from paper).
        
        Enterprise interpretation:
        - Hubs are frequently-involved entities
        - Could be key customers, power users, or critical systems
        - Hub analysis reveals decision-making centralization
        """
        # Sort nodes by degree
        sorted_nodes = sorted(
            self.node_degree.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        hubs = []
        hub_ids = set(node_id for node_id, _ in sorted_nodes)
        
        for node_id, degree in sorted_nodes:
            # Get neighbors
            neighbors = set()
            edge_sizes = []
            
            for edge_id in self.node_to_edges[node_id]:
                edge_nodes = self.edge_to_nodes[edge_id]
                neighbors.update(edge_nodes - {node_id})
                edge_sizes.append(len(edge_nodes))
                
            # Calculate co-occurrence counts
            cooccurrence = Counter()
            for edge_id in self.node_to_edges[node_id]:
                for other in self.edge_to_nodes[edge_id]:
                    if other != node_id:
                        cooccurrence[other] += 1
                        
            # Calculate neighbor density (ego network density)
            neighbor_list = list(neighbors)
            neighbor_edges = 0
            possible_edges = len(neighbors) * (len(neighbors) - 1) / 2
            
            for i, n1 in enumerate(neighbor_list):
                for n2 in neighbor_list[i+1:]:
                    # Check if n1 and n2 appear in same hyperedge
                    edges_n1 = self.node_to_edges[n1]
                    edges_n2 = self.node_to_edges[n2]
                    if edges_n1 & edges_n2:
                        neighbor_edges += 1
                        
            density = neighbor_edges / possible_edges if possible_edges > 0 else 0
            
            stats = NodeStatistics(
                node_id=node_id,
                degree=degree,
                unique_neighbors=len(neighbors),
                neighbor_density=density,
                avg_edge_size=sum(edge_sizes) / len(edge_sizes) if edge_sizes else 0,
                top_cooccurring=cooccurrence.most_common(5)
            )
            hubs.append(stats)
            
        # Calculate hub integration scores
        integration_scores = {}
        for hub in hubs:
            score = sum(
                count for other, count in hub.top_cooccurring
                if other in hub_ids
            )
            integration_scores[hub.node_id] = score
            
        # Calculate rich-club coefficients
        rich_club = self._calculate_rich_club(hub_ids)
        
        return HubAnalysis(
            hubs=hubs,
            hub_integration_scores=integration_scores,
            rich_club_coefficients=rich_club
        )
        
    def _calculate_rich_club(self, hub_ids: Set[str]) -> Dict[int, float]:
        """
        Calculate rich-club coefficients (Table 3 from paper).
        
        Rich-club coefficient measures if high-degree nodes preferentially
        connect to each other.
        
        Enterprise interpretation:
        - High rich-club = decision-making is concentrated among key players
        - Low rich-club = decisions involve diverse participants
        """
        coefficients = {}
        
        for threshold in [10, 20, 50, 100]:
            # Get nodes above threshold
            rich_nodes = {
                node for node, degree in self.node_degree.items()
                if degree >= threshold
            }
            
            if len(rich_nodes) < 2:
                continue
                
            # Count edges among rich nodes
            edges_among_rich = 0
            for edge_id, nodes in self.edge_to_nodes.items():
                rich_in_edge = nodes & rich_nodes
                if len(rich_in_edge) >= 2:
                    # Count pairs
                    edges_among_rich += len(rich_in_edge) * (len(rich_in_edge) - 1) / 2
                    
            # Possible edges among rich nodes
            n = len(rich_nodes)
            possible = n * (n - 1) / 2
            
            coefficients[threshold] = edges_among_rich / possible if possible > 0 else 0
            
        return coefficients
        
    def find_s_components(self, s: int = 1) -> ComponentAnalysis:
        """
        Find s-connected components (Table 4 from paper).
        
        s-connected component: maximal set of hyperedges where every pair
        is linked through a chain of hyperedges sharing at least s nodes.
        
        Enterprise interpretation:
        - High-s components = stable, well-established decision patterns
        - Low-s components = emerging or fragmented decision areas
        
        From paper: "high-s components serving as stable grounding regions 
        for scientific inference, intermediate-s components facilitating 
        cross-domain hypothesis generation, and low-s components revealing 
        areas where conceptual integration remains in flux."
        """
        # Build adjacency for s-connectivity
        edge_ids = list(self.edge_to_nodes.keys())
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        
        for i, e1 in enumerate(edge_ids):
            for e2 in edge_ids[i+1:]:
                overlap = len(self.edge_to_nodes[e1] & self.edge_to_nodes[e2])
                if overlap >= s:
                    adjacency[e1].add(e2)
                    adjacency[e2].add(e1)
                    
        # Find connected components
        visited = set()
        components = []
        
        for edge in edge_ids:
            if edge in visited:
                continue
                
            # BFS to find component
            component = set()
            queue = [edge]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                    
                visited.add(current)
                component.add(current)
                
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)
                        
            components.append(component)
            
        # Sort by size
        components.sort(key=len, reverse=True)
        
        return ComponentAnalysis(
            s_value=s,
            num_components=len(components),
            largest_component_size=len(components[0]) if components else 0,
            top_component_sizes=[len(c) for c in components[:10]],
            component_members=components[:10]
        )
        
    def detect_decision_patterns(self) -> Dict[str, Any]:
        """
        Detect common decision patterns in the hypergraph.
        
        Enterprise-specific analysis not in the paper, but uses
        hypergraph structure to identify:
        - Common approval chains
        - Recurring decision contexts
        - Anomalous patterns
        """
        patterns = {
            "approval_chains": [],
            "common_contexts": [],
            "decision_clusters": [],
            "anomalies": []
        }
        
        # Analyze decision types
        decision_types = Counter(
            event.decision_type for event in self.hypergraph.events
        )
        patterns["decision_type_distribution"] = dict(decision_types)
        
        # Find common participant patterns
        participant_patterns = Counter()
        for event in self.hypergraph.events:
            # Sort participants for consistent pattern matching
            pattern = tuple(sorted(event.participants[:3]))  # First 3
            participant_patterns[pattern] += 1
            
        patterns["common_participant_patterns"] = [
            {"pattern": list(p), "count": c}
            for p, c in participant_patterns.most_common(5)
        ]
        
        # Identify potential anomalies (isolated decisions)
        for event in self.hypergraph.events:
            # Check if any participant appears in very few events
            for participant in event.participants:
                if self.node_degree.get(participant, 0) == 1:
                    patterns["anomalies"].append({
                        "event_id": event.id,
                        "isolated_participant": participant,
                        "reason": "Participant appears in only one decision"
                    })
                    break
                    
        return patterns
        
    def analyze_feedback_potential(self) -> Dict[str, Any]:
        """
        Analyze potential for feedback loop improvement.
        
        From blog: "The key to both operational & analytical context 
        databases isn't the databases themselves. It's the feedback 
        loops within them."
        
        Identifies areas where the context graph could be strengthened:
        - Low-overlap areas (need more linking context)
        - High-degree nodes with low neighbor density (need better resolution)
        - Isolated components (need bridging context)
        """
        analysis = {
            "improvement_areas": [],
            "strength_areas": [],
            "recommendations": []
        }
        
        # Find low-overlap edges
        for event in self.hypergraph.events:
            # Count overlaps with other edges
            overlaps = 0
            for other_event in self.hypergraph.events:
                if other_event.id != event.id:
                    if set(event.participants) & set(other_event.participants):
                        overlaps += 1
                        
            if overlaps == 0:
                analysis["improvement_areas"].append({
                    "type": "isolated_decision",
                    "event_id": event.id,
                    "recommendation": "Add linking context to connect to decision network"
                })
                
        # Find high-degree low-density nodes
        for node, degree in self.node_degree.items():
            if degree > 5:
                # Check neighbor density
                neighbors = set()
                for edge_id in self.node_to_edges[node]:
                    neighbors.update(self.edge_to_nodes[edge_id] - {node})
                    
                # Simple density check
                if len(neighbors) > 10:
                    analysis["improvement_areas"].append({
                        "type": "resolution_candidate",
                        "node": node,
                        "degree": degree,
                        "unique_neighbors": len(neighbors),
                        "recommendation": "May need entity resolution or disambiguation"
                    })
                    
        # S-component analysis for feedback
        s1 = self.find_s_components(s=1)
        s2 = self.find_s_components(s=2)
        
        if s1.num_components > 1:
            analysis["recommendations"].append({
                "type": "connectivity_gap",
                "s1_components": s1.num_components,
                "recommendation": "Add bridging context between component clusters"
            })
            
        if s2.largest_component_size < len(self.hypergraph.events) * 0.5:
            analysis["recommendations"].append({
                "type": "weak_overlap",
                "s2_coverage": s2.largest_component_size / len(self.hypergraph.events),
                "recommendation": "Strengthen overlap by ensuring decisions share multiple entities"
            })
            
        return analysis


def demo_hypergraph_analysis():
    """Demonstrate hypergraph analysis capabilities"""
    from hypergraph_builder import demo_build_enterprise_hypergraph
    
    print("=" * 60)
    print("ENTERPRISE HYPERGRAPH ANALYSIS")
    print("Based on Stewart & Buehler Analysis Framework")
    print("=" * 60)
    
    # Build the hypergraph
    print("\n[1/4] Building Enterprise Context Graph...")
    builder, hypergraph = demo_build_enterprise_hypergraph()
    
    # Create analyzer
    print("[2/4] Creating Analyzer...")
    analyzer = HypergraphAnalyzer(hypergraph)
    
    # Basic statistics
    print("\n" + "=" * 60)
    print("BASIC STATISTICS (Table 1 from paper)")
    print("=" * 60)
    stats = analyzer.get_basic_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
        
    # Degree distribution
    print("\n" + "=" * 60)
    print("DEGREE DISTRIBUTION (Figure 5 from paper)")
    print("=" * 60)
    distribution = analyzer.get_degree_distribution()
    print(f"  Distribution: {distribution}")
    
    slope, r_squared = analyzer.fit_power_law()
    print(f"  Power law exponent: {slope:.3f}")
    print(f"  R-squared: {r_squared:.3f}")
    
    # Hub analysis
    print("\n" + "=" * 60)
    print("HUB ANALYSIS (Table 2 from paper)")
    print("=" * 60)
    hub_analysis = analyzer.identify_hubs(top_k=5)
    
    for hub in hub_analysis.hubs:
        print(f"\n  {hub.node_id}:")
        print(f"    Degree: {hub.degree}")
        print(f"    Unique neighbors: {hub.unique_neighbors}")
        print(f"    Neighbor density: {hub.neighbor_density:.3f}")
        print(f"    Top co-occurring: {hub.top_cooccurring[:3]}")
        
    # S-connected components
    print("\n" + "=" * 60)
    print("S-CONNECTED COMPONENTS (Table 4 from paper)")
    print("=" * 60)
    
    for s in [1, 2]:
        components = analyzer.find_s_components(s=s)
        print(f"\n  s={s}:")
        print(f"    Number of components: {components.num_components}")
        print(f"    Largest component: {components.largest_component_size} edges")
        print(f"    Top sizes: {components.top_component_sizes[:5]}")
        
    # Decision patterns
    print("\n" + "=" * 60)
    print("DECISION PATTERNS (Enterprise-specific)")
    print("=" * 60)
    patterns = analyzer.detect_decision_patterns()
    print(f"  Decision types: {patterns['decision_type_distribution']}")
    print(f"  Common patterns: {len(patterns['common_participant_patterns'])}")
    print(f"  Anomalies detected: {len(patterns['anomalies'])}")
    
    # Feedback analysis
    print("\n" + "=" * 60)
    print("FEEDBACK LOOP ANALYSIS")
    print("=" * 60)
    feedback = analyzer.analyze_feedback_potential()
    print(f"  Improvement areas: {len(feedback['improvement_areas'])}")
    print(f"  Recommendations: {len(feedback['recommendations'])}")
    
    for rec in feedback["recommendations"]:
        print(f"    - {rec['type']}: {rec['recommendation']}")
        
    return analyzer


if __name__ == "__main__":
    demo_hypergraph_analysis()
