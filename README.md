# Enterprise Context Graph

## Implementing Context Graphs Using Hypergraph Research

This implementation adapts the methodology from **"Higher-Order Knowledge Representations for Agentic Scientific Reasoning"** (Stewart & Buehler, MIT, 2026) for enterprise decision-making contexts.

### The Problem

Enterprise AI systems face a fundamental challenge: **context heterogeneity**. As described in recent industry discourse:

> "Instead of five warehouses, we're moving toward hundreds of agents, copilots, and AI applications. Each with its own partial view of the world, its own embedded definitions, its own 'private' context window."

When a renewal agent proposes a 20% discount, it doesn't just pull from the CRM. It pulls from:
- **PagerDuty** for incident history
- **Zendesk** for escalation threads
- **Slack** for VP approval from last quarter
- **Salesforce** for the deal record
- **Snowflake** for usage data
- **The semantic layer** for the definition of "healthy customer"

Traditional pairwise knowledge graphs cannot capture these **n-ary relationships** faithfully.

### The Solution: Hypergraph-Based Context Graphs

This implementation uses **hypergraphs** to capture higher-order relationships:

| Feature | Traditional KG | Hypergraph Context Graph |
|---------|---------------|-------------------------|
| Connection | Pairwise (2 nodes) | n-ary (3+ nodes) |
| Reasoning | Local, multi-hop | Global, high-order correlation |
| Context | Fragmented | Unified/Preserved |
| Complexity | High (combinatorial explosion) | Compact (reduced edge count) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTERPRISE DATA SOURCES                   │
├─────────┬─────────┬─────────┬─────────┬─────────┬──────────┤
│   CRM   │ Support │  Slack  │  Data   │Incident │   HR     │
│         │         │         │Warehouse│         │          │
└────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬─────┘
     │         │         │         │         │         │
     └─────────┴─────────┴────┬────┴─────────┴─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Hypergraph       │
                    │  Builder          │
                    │  (Algorithm 1)    │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Enterprise       │
                    │  Hypergraph       │
                    │  H = (V, E)       │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│   Traversal   │    │   Analysis    │    │  Multi-Agent  │
│   Engine      │    │   Engine      │    │  Reasoning    │
│ (BFS + Yen K) │    │ (s-components)│    │  System       │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Key Components

### 1. Data Models (`models.py`)

Adapts the scientific schema for enterprise use:

```python
class DecisionEvent(BaseModel):
    """A decision event (hyperedge) in the enterprise context graph."""
    participants: List[str]          # N-ary: all entities involved
    decision_type: str               # approval, escalation, renewal
    relation: str                    # The action taken
    operational_context: List[str]   # SOPs, policies referenced
    analytical_context: List[str]    # Metrics, calculations used
    rationale: Optional[str]         # The "why" behind the decision
```

### 2. Hypergraph Construction (`hypergraph_builder.py`)

Implements **Algorithm 1** from the paper with enterprise adaptations:

```python
# Algorithm 1: LLM-guided hypergraph construction with incremental merging
#
# Input: Data from CRM, Support, Communication systems
# Output: Hypergraph H = (V, E), node embeddings Φ
#
# Phase 1: Multi-system ingestion (instead of PDF processing)
# Phase 2: Decision event extraction (dual-pass strategy)
# Phase 3: Entity resolution across systems
# Phase 4: Incremental merging with provenance tracking
```

### 3. Graph Traversal (`traversal.py`)

Implements path-finding with **intersection constraints**:

```python
class PathConstraint:
    intersection_size: int = 1   # Min nodes shared between adjacent hyperedges (IS)
    k_paths: int = 3             # Number of shortest paths (Yen-style)
    max_path_length: int = 10    # Maximum hyperedges in path
```

From the paper:
> "Paths are recovered under a node intersection constraint (S), where adjacent hyperedges must share exactly S nodes."

In enterprise context, requiring `IS ≥ 2` ensures decision paths share meaningful common entities (e.g., same Customer AND same Policy).

### 4. Multi-Agent Reasoning (`agents.py`)

Adapts the paper's agent architecture:

| Scientific Paper | Enterprise Implementation |
|-----------------|--------------------------|
| User | Sales/Support/Finance Agent |
| GraphAgent | ContextAgent |
| Engineer | ExecutiveAgent |
| Hypothesizer | GovernanceAgent |

```
User Query: "Why was Acme given a 20% discount?"
     │
     ▼
ContextAgent: Finds hypergraph paths, extracts context
     │
     ▼
ExecutiveAgent: Interprets mechanistically
     │
     ▼
GovernanceAgent: Verifies compliance, recommends actions
```

### 5. Hypergraph Analysis (`analysis.py`)

Implements analytics from Section 2.2:

- **Degree distribution** (Figure 5): Identify hub entities
- **Hub analysis** (Table 2): Key decision-making players
- **S-connected components** (Table 4): Decision pattern stability
- **Rich-club analysis** (Table 3): Decision concentration

**Enterprise Interpretation:**
- **High-s components** = Stable SOPs, established decision patterns
- **Low-s components** = Areas in flux, emerging patterns
- **Rich-club coefficient** = Decision-making concentration

## Usage

### Quick Demo
```bash
python main.py --quick
```

### Full Demonstration
```bash
python main.py --full
```

### Analysis Only
```bash
python main.py --analysis-only
```

## Example Output

```
=== QUERY: Why was Acme Corp given a 20% discount? ===

[CONTEXT AGENT]
Found 3 relevant decision paths connecting:
  - cust_acme (customer entity)
  - vp_sales (decision maker)
  - deal_001 (deal entity)

Path 1:
  Step 1: escalation - escalated (involving: cust_acme, eng_mike, ticket_101)
    → Connected via: cust_acme
  Step 2: approval - approved (involving: deal_001, vp_sales, rep_jane)
    → Connected via: deal_001

[EXECUTIVE AGENT]
Mechanistic Interpretation:
  The decision trace shows Acme Corp experienced a high-severity incident
  (ticket_101) that was escalated due to SLA breach risk. This incident
  history, combined with the customer's health score of 72 (at-risk threshold),
  justified the 20% discount which was approved by VP Sales.

[GOVERNANCE AGENT]
Compliance Status: COMPLIANT
  ✓ Proper approval chain followed (20% requires VP)
  ✓ Discount policy referenced
  ✓ Precedent exists (Q3 2023 similar situation)

Recommended Actions:
  1. Document this decision as precedent
  2. Schedule 30-day customer check-in
  3. Update customer health score tracking
```

## Theoretical Foundation

### Why Hypergraphs?

From Stewart & Buehler:

> "Traditional pairwise KGs are ill-suited for scientific reasoning as they cannot adequately capture higher-order interactions among multiple entities that often govern emergent physical system behavior."

This applies directly to enterprise decisions where:
- A discount approval involves customer + sales rep + VP + deal + policy
- An escalation involves customer + support agent + engineering + incident + SLA
- These are **irreducible n-ary relationships**

### The Feedback Flywheel

From enterprise AI discourse:

> "The key to both operational & analytical context databases isn't the databases themselves. It's the feedback loops within them."

This implementation supports the flywheel:
1. **Accuracy creates trust**: Hypergraph topology validates reasoning
2. **Trust creates adoption**: Agents query the graph more
3. **Adoption creates feedback**: More decisions → more edges
4. **Feedback creates accuracy**: Entity resolution improves

### Customer-Owned Context

> "Enterprises learned a lesson from cloud data warehouses... This is why Iceberg exists and open table formats are winning."

This implementation uses open formats:
- Pydantic models for schema
- JSON serialization
- No vendor lock-in
- Portable hypergraph representation

## Production Considerations

### Scaling
- Use HyperNetX for hypergraph operations at scale
- Implement embedding-based entity resolution with vector DB
- Add caching layer for frequent traversals

### LLM Integration
```python
# Replace mock extractors with LLM-based extraction
extractor = DecisionEventExtractor(llm_client=openai_client)
```

### Data Connectors
```python
# Real connectors would implement the abstract interface
class SalesforceConnector(EnterpriseDataConnector):
    def fetch_records(self, query, time_range, limit):
        # Salesforce API calls
        pass
```

### Persistence
```python
# Save hypergraph
with open('context_graph.json', 'w') as f:
    json.dump(hypergraph.model_dump(), f)

# Load hypergraph
hypergraph = EnterpriseHypergraph.model_validate(data)
```

## References

1. Stewart, I.A. & Buehler, M.J. (2026). "Higher-Order Knowledge Representations for Agentic Scientific Reasoning." arXiv:2601.04878

2. Ball, J. "Long Live Systems of Record"

3. Gupta, J. & Garg, A. "AI's trillion-dollar opportunity: Context graphs"

4. Tunguz, T. "Operational and Analytical Context Databases"

## License

MIT License - See LICENSE file

## Citation

If you use this implementation, please cite:

```bibtex
@software{enterprise_context_graph,
  title = {Enterprise Context Graph Implementation},
  year = {2026},
  note = {Based on Stewart \& Buehler hypergraph methodology}
}
```
