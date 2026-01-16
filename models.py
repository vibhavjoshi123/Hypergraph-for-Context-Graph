"""
Enterprise Context Graph - Data Models

Adapts the hypergraph methodology from Stewart & Buehler (2026) for enterprise
decision-making contexts. Instead of scientific formulations, we model:
- Decision Traces: The "why" behind business decisions
- Operational Context: SOPs, institutional knowledge
- Analytical Context: Metric definitions, business rules

Based on: "Higher-Order Knowledge Representations for Agentic Scientific Reasoning"
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import datetime
from enum import Enum


class ContextType(str, Enum):
    """Types of context in enterprise systems"""
    OPERATIONAL = "operational"      # SOPs, procedures, institutional knowledge
    ANALYTICAL = "analytical"        # Metrics, calculations, definitions
    DECISION = "decision"            # Decision traces, approvals, outcomes
    ENTITY = "entity"                # Customers, products, employees
    TEMPORAL = "temporal"            # Time-based events, deadlines


class DataSource(str, Enum):
    """Enterprise data sources"""
    CRM = "crm"                      # Salesforce, HubSpot
    SUPPORT = "support"              # Zendesk, ServiceNow
    COMMUNICATION = "communication"  # Slack, Teams, Email
    DATA_WAREHOUSE = "data_warehouse"  # Snowflake, Databricks, BigQuery
    INCIDENT = "incident"            # PagerDuty, Opsgenie
    HR = "hr"                        # Workday, BambooHR
    FINANCE = "finance"              # NetSuite, SAP
    CUSTOM = "custom"


class Entity(BaseModel):
    """
    An enterprise entity node in the hypergraph.
    
    Unlike scientific entities (materials, chemicals), enterprise entities
    represent business objects with rich metadata for governance.
    """
    id: str
    name: str
    entity_type: str  # customer, deal, incident, employee, product, etc.
    source_system: DataSource
    context_type: ContextType = ContextType.ENTITY
    attributes: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified: datetime = Field(default_factory=datetime.now)
    
    # Provenance tracking (critical for enterprise governance)
    source_record_id: Optional[str] = None
    confidence_score: float = 1.0
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.id == other.id
        return False


class DecisionEvent(BaseModel):
    """
    A decision event (hyperedge) in the enterprise context graph.
    
    This is the enterprise analog of the scientific 'Event' class.
    Instead of source/target materials and relations, we capture:
    - Participants: All entities involved in the decision
    - Decision type: What kind of decision was made
    - Context: The operational/analytical context used
    - Outcome: The result of the decision
    
    Key insight from paper: Hyperedges capture n-ary relationships that
    pairwise graphs cannot represent faithfully.
    """
    id: str
    
    # Participants in this decision (n-ary relationship)
    participants: List[str] = Field(
        description="Entity IDs involved in this decision"
    )
    
    # Decision metadata
    decision_type: str  # approval, escalation, renewal, discount, etc.
    relation: str       # The semantic relationship (approved, escalated, etc.)
    
    # Context that informed the decision
    operational_context: List[str] = Field(
        default_factory=list,
        description="SOPs, policies, precedents referenced"
    )
    analytical_context: List[str] = Field(
        default_factory=list,
        description="Metrics, calculations, definitions used"
    )
    
    # Decision trace
    decision_maker: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    outcome: Optional[str] = None
    rationale: Optional[str] = None
    
    # Provenance
    source_systems: List[DataSource] = Field(default_factory=list)
    source_chunk_id: Optional[str] = None
    confidence_score: float = 1.0
    
    # Raw text evidence
    evidence_text: Optional[str] = None
    
    def to_hyperedge(self) -> Set[str]:
        """Convert to hyperedge format (set of node IDs)"""
        return set(self.participants)


class EnterpriseHypergraph(BaseModel):
    """
    Container for enterprise decision events forming a hypergraph.
    
    Analogous to the Hypergraph class in the paper, but with
    enterprise-specific metadata and governance features.
    """
    events: List[DecisionEvent] = Field(default_factory=list)
    
    # Metadata
    name: str = "Enterprise Context Graph"
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    # Governance
    owner: Optional[str] = None
    access_policy: Dict[str, Any] = Field(default_factory=dict)


class ContextDefinition(BaseModel):
    """
    Defines a piece of analytical or operational context.
    
    From the blog: "Analytical context databases are the evolution of 
    semantic layers: definitions and calculations for metrics."
    """
    id: str
    name: str
    context_type: ContextType
    
    # For analytical context
    definition: Optional[str] = None  # Natural language definition
    calculation: Optional[str] = None  # SQL or formula
    dependencies: List[str] = Field(default_factory=list)
    
    # For operational context
    procedure: Optional[str] = None  # SOP text
    exceptions: List[str] = Field(default_factory=list)
    precedents: List[str] = Field(default_factory=list)
    
    # Source
    source_system: Optional[DataSource] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    owner: Optional[str] = None


class PathConstraint(BaseModel):
    """
    Constraints for hypergraph path traversal.
    
    From paper: "Paths are recovered under a node intersection constraint (S),
    where adjacent hyperedges must share exactly S nodes."
    
    In enterprise context, this ensures decision paths share meaningful
    common entities (e.g., same customer AND same policy).
    """
    intersection_size: int = Field(
        default=1,
        ge=1,
        description="Minimum nodes shared between adjacent hyperedges"
    )
    max_path_length: int = Field(
        default=10,
        ge=1,
        description="Maximum number of hyperedges in path"
    )
    k_paths: int = Field(
        default=3,
        ge=1,
        description="Number of shortest paths to return (Yen-style)"
    )
    
    # Enterprise-specific constraints
    required_context_types: List[ContextType] = Field(
        default_factory=list,
        description="Path must include these context types"
    )
    required_sources: List[DataSource] = Field(
        default_factory=list,
        description="Path must include nodes from these systems"
    )
    time_window: Optional[tuple] = Field(
        default=None,
        description="(start_datetime, end_datetime) for temporal filtering"
    )


class HypergraphPath(BaseModel):
    """
    A path through the enterprise hypergraph.
    
    Represents a chain of decision events connected through shared entities,
    providing the mechanistic explanation for how concepts relate.
    """
    path_id: str
    start_node: str
    end_node: str
    
    # Sequence of hyperedges (decision events)
    hyperedges: List[str] = Field(description="Decision event IDs in order")
    
    # Intersection nodes at each step
    intersection_nodes: List[List[str]] = Field(
        description="Shared nodes between adjacent hyperedges"
    )
    
    # Path metrics
    path_length: int
    total_intersection_size: int
    confidence_score: float = 1.0
    
    # Natural language explanation
    explanation: Optional[str] = None


class AgentQuery(BaseModel):
    """
    Query from an agent to the context graph.
    
    Agents (sales, support, finance) query the graph for decision context.
    """
    query_id: str
    agent_type: str  # sales_agent, support_agent, finance_agent
    
    # Query parameters
    start_concepts: List[str]  # Starting entities/concepts
    end_concepts: List[str]    # Target entities/concepts
    query_text: str            # Natural language query
    
    # Constraints
    constraints: PathConstraint = Field(default_factory=PathConstraint)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = Field(default=1, ge=1, le=5)


class AgentResponse(BaseModel):
    """
    Response from the context graph to an agent query.
    
    Contains the mechanistic paths and synthesized context.
    """
    query_id: str
    
    # Retrieved paths
    paths: List[HypergraphPath] = Field(default_factory=list)
    
    # Synthesized context (dicts with context info)
    operational_context: List[Dict[str, Any]] = Field(default_factory=list)
    analytical_context: List[Dict[str, Any]] = Field(default_factory=list)
    
    # For downstream reasoning
    context_summary: Optional[str] = None
    recommended_actions: List[str] = Field(default_factory=list)
    
    # Provenance
    sources_used: List[DataSource] = Field(default_factory=list)
    confidence_score: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.now)
