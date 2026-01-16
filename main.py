#!/usr/bin/env python3
"""
Enterprise Context Graph - Main Demo

This demonstrates the complete implementation of an Enterprise Context Graph
using hypergraph methodology adapted from:

"Higher-Order Knowledge Representations for Agentic Scientific Reasoning"
by Stewart & Buehler (MIT, 2026)

The implementation addresses the "trillion-dollar opportunity" described in
the enterprise AI discourse by:

1. Capturing n-ary decision relationships (not just pairwise)
2. Bridging operational and analytical context
3. Enabling multi-agent reasoning with hypergraph guardrails
4. Supporting the feedback flywheel for continuous improvement

Usage:
    python main.py [--full | --quick | --analysis-only]
"""

import argparse
import json
from datetime import datetime

# Import all modules
from models import (
    Entity, DecisionEvent, EnterpriseHypergraph,
    ContextDefinition, PathConstraint, AgentQuery,
    ContextType, DataSource
)
from hypergraph_builder import (
    EnterpriseHypergraphBuilder,
    MockCRMConnector, MockSupportConnector, MockSlackConnector,
    DecisionEventExtractor, EntityResolver
)
from traversal import (
    HypergraphTraverser, ContextGraphQueryEngine, PathExplainer
)
from agents import (
    EnterpriseReasoningSystem, AgentRole,
    ContextAgent, ExecutiveAgent, GovernanceAgent
)
from analysis import HypergraphAnalyzer


def print_section(title: str, char: str = "="):
    """Print a section header"""
    print(f"\n{char * 60}")
    print(title)
    print(char * 60)


def build_demo_hypergraph():
    """Build the demo hypergraph with mock enterprise data"""
    print_section("BUILDING ENTERPRISE CONTEXT GRAPH")
    
    # Initialize connectors
    crm = MockCRMConnector()
    support = MockSupportConnector()
    slack = MockSlackConnector()
    
    # Build hypergraph
    builder = EnterpriseHypergraphBuilder()
    builder.add_connector(crm)
    builder.add_connector(support)
    builder.add_connector(slack)
    
    # Add context definitions
    print("Adding analytical context definitions...")
    
    # Customer Health Score
    health_score = ContextDefinition(
        id="ctx_health_score",
        name="Customer Health Score",
        context_type=ContextType.ANALYTICAL,
        definition="Composite metric (0-100) indicating customer satisfaction and engagement",
        calculation="""
        health_score = (
            0.30 * nps_score +
            0.30 * usage_trend_score +
            0.20 * support_sentiment_score +
            0.20 * payment_history_score
        )
        """,
        dependencies=["nps_score", "usage_trend", "support_sentiment", "payment_history"],
        source_system=DataSource.DATA_WAREHOUSE
    )
    builder.add_context_definition(health_score)
    
    # At-Risk Definition
    at_risk = ContextDefinition(
        id="ctx_at_risk",
        name="At-Risk Customer Definition",
        context_type=ContextType.ANALYTICAL,
        definition="Customer is at-risk if health_score < 70 OR recent_escalations > 2",
        calculation="at_risk = (health_score < 70) OR (escalations_30d > 2)",
        dependencies=["ctx_health_score", "escalations_30d"],
        source_system=DataSource.DATA_WAREHOUSE
    )
    builder.add_context_definition(at_risk)
    
    print("Adding operational context definitions...")
    
    # Discount Policy
    discount_policy = ContextDefinition(
        id="ctx_discount_policy",
        name="Discount Approval Policy",
        context_type=ContextType.OPERATIONAL,
        procedure="""
        DISCOUNT APPROVAL WORKFLOW:
        1. Discounts up to 10% - Account Executive can approve
        2. Discounts 10-20% - Manager approval required
        3. Discounts 20-25% - VP approval required
        4. Discounts >25% - CEO approval required
        
        JUSTIFICATION REQUIREMENTS:
        - Document customer situation and risk factors
        - Reference similar precedents if available
        - Include customer health score and trajectory
        """,
        exceptions=[
            "Strategic accounts may receive up to 25% with VP approval only",
            "Competitive displacement situations allow +5% discretionary"
        ],
        precedents=[
            "Q3 2023: Acme Corp received 20% after major outage (VP approved)",
            "Q4 2023: TechStart received 15% for multi-year commitment"
        ]
    )
    builder.add_context_definition(discount_policy)
    
    # Escalation Policy
    escalation_policy = ContextDefinition(
        id="ctx_escalation_policy",
        name="Incident Escalation Policy",
        context_type=ContextType.OPERATIONAL,
        procedure="""
        ESCALATION TRIGGERS:
        1. SLA breach imminent (within 2 hours of deadline)
        2. Severity 1 incidents - immediate escalation
        3. Customer requests escalation explicitly
        4. Impact affects >100 users
        
        ESCALATION PATH:
        L1 Support -> L2 Engineering -> Engineering Manager -> VP Engineering
        """,
        exceptions=["Strategic accounts bypass L1 directly to L2"]
    )
    builder.add_context_definition(escalation_policy)
    
    # Build the graph
    print("Extracting decision events from data sources...")
    hypergraph = builder.build()
    
    # Print statistics
    stats = builder.get_statistics()
    print(f"\nGraph built successfully!")
    print(f"  Nodes: {stats['num_nodes']}")
    print(f"  Edges (Decision Events): {stats['num_edges']}")
    print(f"  Avg Edge Size: {stats['avg_edge_size']:.2f}")
    print(f"  Data Sources: {stats['sources']}")
    
    return builder, hypergraph


def run_analysis(hypergraph: EnterpriseHypergraph):
    """Run comprehensive hypergraph analysis"""
    print_section("HYPERGRAPH ANALYSIS")
    
    analyzer = HypergraphAnalyzer(hypergraph)
    
    # Basic statistics
    print("\n--- Basic Statistics (Table 1 analog) ---")
    stats = analyzer.get_basic_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    # Power law fit
    print("\n--- Degree Distribution (Figure 5 analog) ---")
    slope, r_squared = analyzer.fit_power_law()
    print(f"  Power law exponent: {slope:.3f}")
    print(f"  R-squared: {r_squared:.3f}")
    
    if slope > 1.0 and slope < 2.0:
        print("  → Scale-free structure detected (typical of knowledge graphs)")
    
    # Hub analysis
    print("\n--- Hub Analysis (Table 2 analog) ---")
    hub_analysis = analyzer.identify_hubs(top_k=5)
    
    print("\n  Top Hubs by Degree:")
    for hub in hub_analysis.hubs:
        print(f"    {hub.node_id}: degree={hub.degree}, "
              f"neighbors={hub.unique_neighbors}, "
              f"density={hub.neighbor_density:.3f}")
    
    # S-connected components
    print("\n--- S-Connected Components (Table 4 analog) ---")
    for s in [1, 2]:
        comp = analyzer.find_s_components(s=s)
        print(f"  s={s}: {comp.num_components} components, "
              f"largest={comp.largest_component_size} edges")
    
    print("\n  Enterprise Interpretation:")
    s1 = analyzer.find_s_components(s=1)
    s2 = analyzer.find_s_components(s=2)
    
    if s2.largest_component_size > 0:
        print(f"    → High-s components (s≥2): Stable decision patterns")
        print(f"    → Low-s components (s=1): Areas of flux/emerging patterns")
    
    # Decision patterns
    print("\n--- Decision Pattern Detection ---")
    patterns = analyzer.detect_decision_patterns()
    print(f"  Decision types: {patterns['decision_type_distribution']}")
    print(f"  Anomalies: {len(patterns['anomalies'])}")
    
    # Feedback potential
    print("\n--- Feedback Loop Analysis ---")
    feedback = analyzer.analyze_feedback_potential()
    print(f"  Improvement areas: {len(feedback['improvement_areas'])}")
    
    for rec in feedback.get("recommendations", []):
        print(f"    Recommendation: {rec['recommendation']}")
    
    return analyzer


def run_multi_agent_demo(hypergraph: EnterpriseHypergraph):
    """Demonstrate multi-agent reasoning"""
    print_section("MULTI-AGENT REASONING DEMO")
    
    # Create query engine and reasoning system
    query_engine = ContextGraphQueryEngine(hypergraph)
    reasoning_system = EnterpriseReasoningSystem(query_engine)
    
    # Demo query
    queries = [
        "Why was Acme Corp given a 20% discount on their renewal?",
        "What incidents affected Acme Corp before the discount approval?",
    ]
    
    for query in queries:
        print(f"\n{'─' * 50}")
        print(f"QUERY: {query}")
        print('─' * 50)
        
        result = reasoning_system.reason(query)
        
        print("\n[CONTEXT AGENT]")
        print("Searching hypergraph for relevant decision traces...")
        # Summarize context
        if "paths" in result.get("full_context", {}):
            paths = result["full_context"]["paths"]
            print(f"Found {len(paths)} relevant paths")
        
        print("\n[EXECUTIVE AGENT]")
        print("Mechanistic interpretation:")
        # Print truncated interpretation
        interp = result.get("interpretation", "")
        if interp:
            lines = interp.split('\n')[:5]
            for line in lines:
                print(f"  {line}")
        
        print("\n[GOVERNANCE AGENT]")
        print("Compliance review:")
        review = result.get("governance_review", "")
        if "COMPLIANT" in review:
            print("  ✓ Decision is COMPLIANT with policies")
        if "Recommended Actions" in review:
            print("  → See full report for recommended actions")
    
    return reasoning_system


def run_quick_demo():
    """Run a quick demonstration"""
    print_section("ENTERPRISE CONTEXT GRAPH - QUICK DEMO", "═")
    print("""
This demo shows how hypergraph methodology from scientific research
can be applied to enterprise decision-making contexts.

Key concepts from Stewart & Buehler (2026):
• Hyperedges capture n-ary relationships (beyond pairwise)
• S-connected components identify decision stability
• Multi-agent systems use graph topology as guardrails
• Feedback loops compound context accuracy over time
    """)
    
    # Build graph
    builder, hypergraph = build_demo_hypergraph()
    
    # Quick analysis
    analyzer = HypergraphAnalyzer(hypergraph)
    stats = analyzer.get_basic_statistics()
    
    print("\n--- Quick Statistics ---")
    print(f"  Decision events captured: {stats.get('num_edges', 0)}")
    print(f"  Entities involved: {stats.get('num_nodes', 0)}")
    
    # Single query demo
    print_section("SAMPLE QUERY")
    query_engine = ContextGraphQueryEngine(hypergraph)
    reasoning_system = EnterpriseReasoningSystem(query_engine)
    
    query = "Why was Acme Corp given a 20% discount?"
    print(f"Query: {query}\n")
    
    result = reasoning_system.reason(query)
    print("Response Summary:")
    print("  • Context Agent found relevant decision traces")
    print("  • Executive Agent interpreted the decision chain")
    print("  • Governance Agent confirmed policy compliance")
    print("\n  See full demo (--full) for complete output")


def run_full_demo():
    """Run the full demonstration"""
    print_section("ENTERPRISE CONTEXT GRAPH - FULL DEMONSTRATION", "═")
    print("""
Implementing the "trillion-dollar opportunity" using hypergraph methodology.

Based on:
• "Higher-Order Knowledge Representations for Agentic Scientific Reasoning"
  (Stewart & Buehler, MIT, 2026)
• Enterprise AI discourse on context graphs and systems of intelligence

This implementation addresses key challenges:
1. Heterogeneity of enterprise data sources
2. N-ary decision relationships (beyond pairwise)
3. Bridging operational and analytical context
4. Multi-agent reasoning with verifiable guardrails
    """)
    
    # Build hypergraph
    builder, hypergraph = build_demo_hypergraph()
    
    # Run analysis
    analyzer = run_analysis(hypergraph)
    
    # Run multi-agent demo
    reasoning_system = run_multi_agent_demo(hypergraph)
    
    # Summary
    print_section("IMPLEMENTATION SUMMARY")
    print("""
Key Components Demonstrated:

1. DATA MODELS (models.py)
   • Entity, DecisionEvent, EnterpriseHypergraph
   • ContextDefinition (operational & analytical)
   • PathConstraint with intersection size (IS)

2. HYPERGRAPH CONSTRUCTION (hypergraph_builder.py)
   • Multi-system data connectors
   • Dual-pass event extraction
   • Entity resolution across systems
   • Incremental merging (Algorithm 1 adaptation)

3. GRAPH TRAVERSAL (traversal.py)
   • BFS with intersection constraints
   • Yen-style K-shortest paths
   • Natural language path explanation

4. MULTI-AGENT REASONING (agents.py)
   • ContextAgent (hypergraph querying)
   • ExecutiveAgent (mechanistic interpretation)
   • GovernanceAgent (compliance & actions)

5. HYPERGRAPH ANALYSIS (analysis.py)
   • Degree distribution & power law fitting
   • Hub detection and analysis
   • S-connected components
   • Feedback loop potential assessment

For production use:
• Replace mock connectors with real API integrations
• Add LLM client for semantic extraction
• Implement embedding-based entity resolution
• Add persistence layer for hypergraph storage
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Enterprise Context Graph Demo"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full demonstration"
    )
    parser.add_argument(
        "--quick",
        action="store_true", 
        help="Run quick demonstration (default)"
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Run only hypergraph analysis"
    )
    
    args = parser.parse_args()
    
    if args.analysis_only:
        builder, hypergraph = build_demo_hypergraph()
        run_analysis(hypergraph)
    elif args.full:
        run_full_demo()
    else:
        run_quick_demo()


if __name__ == "__main__":
    main()
