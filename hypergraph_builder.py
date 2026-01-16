"""
Enterprise Hypergraph Construction

Adapts Algorithm 1 from Stewart & Buehler for enterprise decision traces.
Instead of processing scientific manuscripts, we process:
- CRM records (deals, contacts, activities)
- Support tickets (escalations, resolutions)
- Communication logs (Slack, email approvals)
- Data warehouse queries (usage metrics, health scores)

Key adaptations:
1. Document preprocessing → Multi-system data ingestion
2. Dual-pass extraction → Decision trace extraction
3. Semantic deduplication → Entity resolution across systems
"""

import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict
import uuid

from models import (
    Entity, DecisionEvent, EnterpriseHypergraph,
    ContextDefinition, ContextType, DataSource
)


class EnterpriseDataConnector:
    """
    Abstract connector for enterprise data sources.
    
    In production, this would have implementations for:
    - Salesforce, HubSpot (CRM)
    - Zendesk, ServiceNow (Support)
    - Slack, Teams (Communication)
    - Snowflake, Databricks (Data Warehouse)
    """
    
    def __init__(self, source: DataSource, config: Dict[str, Any]):
        self.source = source
        self.config = config
        
    def fetch_records(
        self,
        query: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Fetch records from the data source"""
        raise NotImplementedError
        
    def get_schema(self) -> Dict[str, Any]:
        """Get schema information for entity resolution"""
        raise NotImplementedError


class MockCRMConnector(EnterpriseDataConnector):
    """Mock CRM connector for demonstration"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(DataSource.CRM, config or {})
        
    def fetch_records(self, **kwargs) -> List[Dict[str, Any]]:
        """Return sample CRM records"""
        return [
            {
                "id": "deal_001",
                "type": "deal",
                "customer_id": "cust_acme",
                "customer_name": "Acme Corp",
                "deal_value": 150000,
                "stage": "renewal",
                "health_score": 72,
                "owner": "rep_jane",
                "last_activity": "2024-01-10T14:30:00Z",
                "notes": "Customer requested 20% discount due to recent incidents"
            },
            {
                "id": "deal_002", 
                "type": "deal",
                "customer_id": "cust_globex",
                "customer_name": "Globex Industries",
                "deal_value": 280000,
                "stage": "expansion",
                "health_score": 91,
                "owner": "rep_john",
                "last_activity": "2024-01-12T09:15:00Z",
                "notes": "Expanding to enterprise tier"
            }
        ]


class MockSupportConnector(EnterpriseDataConnector):
    """Mock Support connector for demonstration"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(DataSource.SUPPORT, config or {})
        
    def fetch_records(self, **kwargs) -> List[Dict[str, Any]]:
        """Return sample support records"""
        return [
            {
                "id": "ticket_101",
                "type": "incident",
                "customer_id": "cust_acme",
                "severity": "high",
                "status": "resolved",
                "created": "2024-01-05T08:00:00Z",
                "resolved": "2024-01-05T14:30:00Z",
                "resolution_time_hours": 6.5,
                "escalated": True,
                "escalation_reason": "SLA breach risk",
                "assigned_to": "eng_mike"
            },
            {
                "id": "ticket_102",
                "type": "support_request",
                "customer_id": "cust_acme",
                "severity": "medium",
                "status": "resolved",
                "created": "2024-01-08T10:00:00Z",
                "resolved": "2024-01-08T16:00:00Z",
                "resolution_time_hours": 6.0,
                "escalated": False,
                "assigned_to": "support_sarah"
            }
        ]


class MockSlackConnector(EnterpriseDataConnector):
    """Mock Slack connector for demonstration"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(DataSource.COMMUNICATION, config or {})
        
    def fetch_records(self, **kwargs) -> List[Dict[str, Any]]:
        """Return sample Slack records (decision traces)"""
        return [
            {
                "id": "msg_001",
                "type": "approval",
                "channel": "deal-approvals",
                "timestamp": "2024-01-10T15:00:00Z",
                "user": "vp_sales",
                "text": "Approved 20% discount for Acme Corp renewal - justified by incident history and retention risk",
                "thread_context": {
                    "deal_id": "deal_001",
                    "requested_by": "rep_jane",
                    "discount_amount": "20%",
                    "approval_reason": "Customer experienced multiple incidents; retention at risk"
                }
            },
            {
                "id": "msg_002",
                "type": "escalation_notification",
                "channel": "incidents",
                "timestamp": "2024-01-05T09:30:00Z",
                "user": "eng_mike",
                "text": "Escalating Acme ticket - approaching SLA breach",
                "thread_context": {
                    "ticket_id": "ticket_101",
                    "customer_id": "cust_acme",
                    "escalation_type": "sla_risk"
                }
            }
        ]


class DecisionEventExtractor:
    """
    Extracts decision events from enterprise data.
    
    Implements the dual-pass strategy from the paper:
    - Pass 1: Explicit decision traces (approvals, escalations)
    - Pass 2: Implicit relationships (usage patterns, precedents)
    
    In production, this would use an LLM for semantic extraction.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.extraction_prompts = self._load_extraction_prompts()
        
    def _load_extraction_prompts(self) -> Dict[str, str]:
        """Load prompts for LLM-based extraction"""
        return {
            "decision_trace": """
Extract decision events from the following enterprise data. For each decision:
1. Identify all participating entities (customers, employees, products, tickets)
2. Identify the decision type (approval, escalation, renewal, discount, etc.)
3. Identify the relation/action taken
4. Extract any referenced policies, SOPs, or precedents (operational context)
5. Extract any metrics or calculations mentioned (analytical context)
6. Note the decision outcome and rationale

Return as JSON with the following structure:
{
    "participants": ["entity_id_1", "entity_id_2", ...],
    "decision_type": "type",
    "relation": "action_taken",
    "operational_context": ["policy_1", "precedent_1"],
    "analytical_context": ["metric_1", "calculation_1"],
    "outcome": "result",
    "rationale": "explanation"
}

Data to process:
""",
            "entity_resolution": """
Determine if these two entities refer to the same real-world object.
Consider name variations, IDs, and contextual information.

Entity 1: {entity1}
Entity 2: {entity2}

Return: {"same_entity": true/false, "confidence": 0.0-1.0, "canonical_name": "preferred name"}
"""
        }
    
    def extract_from_crm(self, record: Dict[str, Any]) -> List[DecisionEvent]:
        """Extract decision events from CRM records"""
        events = []
        
        # Extract renewal decisions
        if record.get("stage") == "renewal":
            event = DecisionEvent(
                id=f"evt_{record['id']}_{uuid.uuid4().hex[:8]}",
                participants=[
                    record["customer_id"],
                    record.get("owner", "unknown"),
                    record["id"]
                ],
                decision_type="renewal_assessment",
                relation="assessed_for_renewal",
                operational_context=["renewal_playbook"],
                analytical_context=[
                    f"health_score:{record.get('health_score', 'unknown')}"
                ],
                source_systems=[DataSource.CRM],
                source_chunk_id=record["id"],
                evidence_text=record.get("notes", "")
            )
            events.append(event)
            
        return events
    
    def extract_from_support(self, record: Dict[str, Any]) -> List[DecisionEvent]:
        """Extract decision events from support records"""
        events = []
        
        # Extract escalation decisions
        if record.get("escalated"):
            event = DecisionEvent(
                id=f"evt_{record['id']}_{uuid.uuid4().hex[:8]}",
                participants=[
                    record["customer_id"],
                    record.get("assigned_to", "unknown"),
                    record["id"]
                ],
                decision_type="escalation",
                relation="escalated",
                operational_context=[
                    f"escalation_reason:{record.get('escalation_reason', 'unknown')}"
                ],
                analytical_context=[
                    f"severity:{record.get('severity', 'unknown')}",
                    f"resolution_time:{record.get('resolution_time_hours', 'unknown')}h"
                ],
                source_systems=[DataSource.SUPPORT],
                source_chunk_id=record["id"],
                outcome=record.get("status", "unknown")
            )
            events.append(event)
            
        # Extract resolution events
        if record.get("status") == "resolved":
            event = DecisionEvent(
                id=f"evt_resolved_{record['id']}_{uuid.uuid4().hex[:8]}",
                participants=[
                    record["customer_id"],
                    record.get("assigned_to", "unknown"),
                    record["id"]
                ],
                decision_type="resolution",
                relation="resolved",
                analytical_context=[
                    f"resolution_time:{record.get('resolution_time_hours', 'unknown')}h"
                ],
                source_systems=[DataSource.SUPPORT],
                source_chunk_id=record["id"]
            )
            events.append(event)
            
        return events
    
    def extract_from_communication(self, record: Dict[str, Any]) -> List[DecisionEvent]:
        """Extract decision events from communication records"""
        events = []
        
        # Extract approval decisions
        if record.get("type") == "approval":
            context = record.get("thread_context", {})
            event = DecisionEvent(
                id=f"evt_{record['id']}_{uuid.uuid4().hex[:8]}",
                participants=[
                    context.get("deal_id", "unknown"),
                    record.get("user", "unknown"),
                    context.get("requested_by", "unknown")
                ],
                decision_type="approval",
                relation="approved",
                decision_maker=record.get("user"),
                operational_context=[
                    f"discount_policy:{context.get('discount_amount', 'unknown')}"
                ],
                rationale=context.get("approval_reason", ""),
                source_systems=[DataSource.COMMUNICATION],
                source_chunk_id=record["id"],
                evidence_text=record.get("text", ""),
                timestamp=datetime.fromisoformat(
                    record.get("timestamp", datetime.now().isoformat()).replace("Z", "+00:00")
                )
            )
            events.append(event)
            
        return events
    
    def extract_with_llm(
        self,
        data: Dict[str, Any],
        source: DataSource
    ) -> List[DecisionEvent]:
        """
        Use LLM for semantic extraction (production implementation).
        
        This would call the LLM with structured prompts like the paper's
        dual-pass strategy.
        """
        if self.llm_client is None:
            # Fall back to rule-based extraction
            if source == DataSource.CRM:
                return self.extract_from_crm(data)
            elif source == DataSource.SUPPORT:
                return self.extract_from_support(data)
            elif source == DataSource.COMMUNICATION:
                return self.extract_from_communication(data)
            return []
            
        # LLM-based extraction would go here
        prompt = self.extraction_prompts["decision_trace"] + json.dumps(data, indent=2)
        # response = self.llm_client.complete(prompt)
        # events = self._parse_llm_response(response)
        # return events
        raise NotImplementedError("LLM extraction requires llm_client")


class EntityResolver:
    """
    Resolves entities across different systems.
    
    Implements the embedding-based deduplication from the paper:
    - Compute embeddings for entities
    - Find similar entities (cosine similarity ≥ threshold)
    - Select canonical representative
    
    This is critical for enterprise context graphs because:
    - "Customer X" in CRM might be "Acme Corp" in Support
    - "rep_jane" in CRM might be "Jane Smith" in Slack
    """
    
    def __init__(self, embedding_model=None, similarity_threshold: float = 0.95):
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.entity_registry: Dict[str, Entity] = {}
        self.alias_map: Dict[str, str] = {}  # alias -> canonical_id
        
    def register_entity(self, entity: Entity) -> str:
        """Register an entity and return its canonical ID"""
        # Check for existing match
        canonical_id = self._find_match(entity)
        
        if canonical_id:
            # Add as alias
            self.alias_map[entity.id] = canonical_id
            return canonical_id
        else:
            # Register as new entity
            self.entity_registry[entity.id] = entity
            return entity.id
            
    def _find_match(self, entity: Entity) -> Optional[str]:
        """Find matching entity using embeddings or rules"""
        # Rule-based matching for demo (would use embeddings in production)
        for existing_id, existing_entity in self.entity_registry.items():
            # Same source ID
            if (entity.source_record_id and 
                entity.source_record_id == existing_entity.source_record_id):
                return existing_id
                
            # Name similarity (simplified)
            if self._names_match(entity.name, existing_entity.name):
                return existing_id
                
        return None
        
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names match (simplified)"""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        # Exact match
        if n1 == n2:
            return True
            
        # One contains the other
        if n1 in n2 or n2 in n1:
            return True
            
        return False
        
    def resolve(self, entity_id: str) -> str:
        """Resolve an entity ID to its canonical form"""
        return self.alias_map.get(entity_id, entity_id)
        
    def get_all_aliases(self, canonical_id: str) -> Set[str]:
        """Get all aliases for a canonical entity"""
        aliases = {canonical_id}
        for alias, canon in self.alias_map.items():
            if canon == canonical_id:
                aliases.add(alias)
        return aliases


class EnterpriseHypergraphBuilder:
    """
    Builds enterprise hypergraph from multiple data sources.
    
    Implements Algorithm 1 from the paper with adaptations:
    1. Multi-system ingestion instead of PDF processing
    2. Decision event extraction instead of scientific relation extraction
    3. Entity resolution across systems
    4. Incremental merging with provenance tracking
    """
    
    def __init__(
        self,
        connectors: List[EnterpriseDataConnector] = None,
        extractor: DecisionEventExtractor = None,
        resolver: EntityResolver = None,
        merge_frequency: int = 10
    ):
        self.connectors = connectors or []
        self.extractor = extractor or DecisionEventExtractor()
        self.resolver = resolver or EntityResolver()
        self.merge_frequency = merge_frequency
        
        # Global hypergraph state
        self.hypergraph = EnterpriseHypergraph()
        self.entities: Dict[str, Entity] = {}
        self.events_by_entity: Dict[str, List[str]] = defaultdict(list)
        
    def add_connector(self, connector: EnterpriseDataConnector):
        """Add a data source connector"""
        self.connectors.append(connector)
        
    def build(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        progress_callback=None
    ) -> EnterpriseHypergraph:
        """
        Build the hypergraph from all connected sources.
        
        This is the main entry point that orchestrates:
        1. Data fetching from each source
        2. Event extraction
        3. Entity resolution
        4. Incremental merging
        """
        total_records = 0
        
        for connector in self.connectors:
            records = connector.fetch_records(time_range=time_range)
            
            for i, record in enumerate(records):
                # Extract events
                events = self.extractor.extract_with_llm(record, connector.source)
                
                # Process each event
                for event in events:
                    self._process_event(event)
                    
                total_records += 1
                
                # Periodic entity resolution (like paper's semantic merging)
                if total_records % self.merge_frequency == 0:
                    self._perform_resolution_pass()
                    
                if progress_callback:
                    progress_callback(total_records, connector.source)
                    
        # Final resolution pass
        self._perform_resolution_pass()
        
        return self.hypergraph
        
    def _process_event(self, event: DecisionEvent):
        """Process a single decision event"""
        # Resolve all participant entities
        resolved_participants = []
        for participant_id in event.participants:
            resolved_id = self.resolver.resolve(participant_id)
            resolved_participants.append(resolved_id)
            
            # Track event-entity mapping
            self.events_by_entity[resolved_id].append(event.id)
            
        # Update event with resolved participants
        event.participants = resolved_participants
        
        # Add to hypergraph
        self.hypergraph.events.append(event)
        
    def _perform_resolution_pass(self):
        """Perform entity resolution across all entities"""
        # In production, this would:
        # 1. Compute embeddings for new entities
        # 2. Find similarity clusters
        # 3. Merge synonymous entities
        # 4. Update all references
        pass
        
    def add_context_definition(self, context: ContextDefinition):
        """Add an analytical or operational context definition"""
        # Register as an entity
        entity = Entity(
            id=context.id,
            name=context.name,
            entity_type="context_definition",
            source_system=context.source_system or DataSource.CUSTOM,
            context_type=context.context_type,
            attributes={
                "definition": context.definition,
                "calculation": context.calculation
            }
        )
        self.resolver.register_entity(entity)
        self.entities[context.id] = entity
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get hypergraph statistics (like Table 1 in paper)"""
        if not self.hypergraph.events:
            return {"nodes": 0, "edges": 0}
            
        # Collect all nodes
        all_nodes = set()
        edge_sizes = []
        
        for event in self.hypergraph.events:
            nodes = set(event.participants)
            all_nodes.update(nodes)
            edge_sizes.append(len(nodes))
            
        # Calculate overlap statistics
        edge_pairs_with_overlap = 0
        for i, e1 in enumerate(self.hypergraph.events):
            for e2 in self.hypergraph.events[i+1:]:
                if set(e1.participants) & set(e2.participants):
                    edge_pairs_with_overlap += 1
                    
        return {
            "num_nodes": len(all_nodes),
            "num_edges": len(self.hypergraph.events),
            "avg_edge_size": sum(edge_sizes) / len(edge_sizes) if edge_sizes else 0,
            "max_edge_size": max(edge_sizes) if edge_sizes else 0,
            "edge_pairs_with_overlap": edge_pairs_with_overlap,
            "sources": list(set(
                src.value for event in self.hypergraph.events 
                for src in event.source_systems
            ))
        }


def demo_build_enterprise_hypergraph():
    """
    Demonstrate building an enterprise context graph.
    
    This simulates the scenario from the blog:
    "When a renewal agent proposes a 20% discount, it pulls from:
    - PagerDuty for incident history
    - Zendesk for escalation threads  
    - Slack for the VP approval from last quarter
    - Salesforce for the deal record
    - Snowflake for usage data"
    """
    # Initialize connectors
    crm = MockCRMConnector()
    support = MockSupportConnector()
    slack = MockSlackConnector()
    
    # Build hypergraph
    builder = EnterpriseHypergraphBuilder()
    builder.add_connector(crm)
    builder.add_connector(support)
    builder.add_connector(slack)
    
    # Add context definitions (analytical context)
    health_score_def = ContextDefinition(
        id="ctx_health_score",
        name="Customer Health Score",
        context_type=ContextType.ANALYTICAL,
        definition="Composite metric indicating customer satisfaction and engagement",
        calculation="0.3*NPS + 0.3*usage_trend + 0.2*support_sentiment + 0.2*payment_history",
        source_system=DataSource.DATA_WAREHOUSE
    )
    builder.add_context_definition(health_score_def)
    
    # Add operational context
    discount_policy = ContextDefinition(
        id="ctx_discount_policy",
        name="Discount Approval Policy",
        context_type=ContextType.OPERATIONAL,
        procedure="Discounts >15% require VP approval. Consider incident history and retention risk.",
        exceptions=["Strategic accounts may receive up to 25% with CEO approval"],
        precedents=["Q3 2023: Acme Corp received 20% due to major outage"]
    )
    builder.add_context_definition(discount_policy)
    
    # Build the graph
    hypergraph = builder.build()
    
    # Print statistics
    stats = builder.get_statistics()
    print("\n=== Enterprise Context Graph Statistics ===")
    print(f"Nodes: {stats['num_nodes']}")
    print(f"Edges (Decision Events): {stats['num_edges']}")
    print(f"Avg Edge Size: {stats['avg_edge_size']:.2f}")
    print(f"Sources: {stats['sources']}")
    
    print("\n=== Decision Events ===")
    for event in hypergraph.events:
        print(f"\nEvent: {event.id}")
        print(f"  Type: {event.decision_type}")
        print(f"  Participants: {event.participants}")
        print(f"  Relation: {event.relation}")
        if event.rationale:
            print(f"  Rationale: {event.rationale}")
            
    return builder, hypergraph


if __name__ == "__main__":
    demo_build_enterprise_hypergraph()
