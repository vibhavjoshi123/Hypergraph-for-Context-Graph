"""
Enterprise Multi-Agent Reasoning System

Adapts the multi-agent framework from Stewart & Buehler for enterprise contexts.

From paper (Figure 8):
- User: Submits a question connecting concepts
- GraphAgent: Locates entities in hypergraph, extracts induced subgraph
- Engineer: Interprets subgraph mechanistically
- Hypothesizer: Proposes testable hypotheses

Enterprise adaptation:
- User/Agent: Sales, Support, Finance agents submit queries
- ContextAgent: Finds relevant decision traces in context graph
- ExecutiveAgent: Interprets decision paths mechanistically
- GovernanceAgent: Ensures compliance with policies, proposes actions

This creates a "teacherless" system where hypergraph topology acts as
verifiable guardrails for agent reasoning.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from models import (
    AgentQuery, AgentResponse, PathConstraint,
    HypergraphPath, ContextType, DataSource
)
from traversal import ContextGraphQueryEngine, HypergraphTraverser


class AgentRole(str, Enum):
    """Agent roles in the enterprise reasoning system"""
    CONTEXT_AGENT = "context_agent"      # Finds context in hypergraph
    EXECUTIVE_AGENT = "executive_agent"  # Interprets mechanistically
    GOVERNANCE_AGENT = "governance_agent"  # Ensures compliance
    SALES_AGENT = "sales_agent"          # Domain: Sales decisions
    SUPPORT_AGENT = "support_agent"      # Domain: Support decisions
    FINANCE_AGENT = "finance_agent"      # Domain: Finance decisions


@dataclass
class AgentMessage:
    """Message passed between agents"""
    sender: AgentRole
    recipient: AgentRole
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender.value,
            "recipient": self.recipient.value,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AgentState:
    """State maintained by each agent"""
    role: AgentRole
    conversation_history: List[AgentMessage] = field(default_factory=list)
    current_context: Dict[str, Any] = field(default_factory=dict)
    tools_available: List[str] = field(default_factory=list)


class BaseAgent:
    """Base class for all agents in the system"""
    
    def __init__(self, role: AgentRole, llm_client=None):
        self.role = role
        self.llm_client = llm_client
        self.state = AgentState(role=role)
        self.system_prompt = self._build_system_prompt()
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent"""
        raise NotImplementedError
        
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and generate response"""
        raise NotImplementedError
        
    def _call_llm(self, user_message: str, context: Dict[str, Any] = None) -> str:
        """Call the LLM with the message (mock for demo)"""
        if self.llm_client is None:
            # Return mock response for demo
            return self._mock_response(user_message, context)
        # Real LLM call would go here
        raise NotImplementedError
        
    def _mock_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate mock response for demonstration"""
        return f"[{self.role.value}] Processed: {message[:100]}..."


class ContextAgent(BaseAgent):
    """
    Agent that queries the hypergraph for relevant context.
    
    Analogous to GraphAgent in the paper:
    - Extracts keywords from query
    - Matches to hypergraph nodes
    - Finds shortest paths
    - Returns induced subgraph
    """
    
    def __init__(self, query_engine: ContextGraphQueryEngine, llm_client=None):
        super().__init__(AgentRole.CONTEXT_AGENT, llm_client)
        self.query_engine = query_engine
        self.state.tools_available = [
            "search_hypergraph",
            "find_paths",
            "get_entity_neighbors",
            "get_decision_history"
        ]
        
    def _build_system_prompt(self) -> str:
        return """You are a Context Agent responsible for finding relevant 
decision context from the enterprise hypergraph.

Your capabilities:
1. Extract key entities from queries (customers, deals, employees, etc.)
2. Find paths in the hypergraph connecting concepts
3. Retrieve operational context (SOPs, policies, precedents)
4. Retrieve analytical context (metrics, definitions)

When given a query:
1. Identify the key entities mentioned
2. Search the hypergraph for these entities
3. Find paths between relevant concepts
4. Return the context needed for decision-making

Always cite the source events and systems for your findings."""

    def process(self, message: AgentMessage) -> AgentMessage:
        """Process query and return hypergraph context"""
        query_text = message.content
        
        # Extract entities from query (would use LLM in production)
        entities = self._extract_entities(query_text)
        
        # Build and execute query
        query = AgentQuery(
            query_id=f"q_{datetime.now().timestamp()}",
            agent_type=message.sender.value,
            start_concepts=entities.get("start", []),
            end_concepts=entities.get("end", []),
            query_text=query_text,
            constraints=PathConstraint(
                intersection_size=message.context.get("intersection_size", 1),
                k_paths=message.context.get("k_paths", 3)
            )
        )
        
        response = self.query_engine.query(query)
        
        # Format response for next agent
        context_summary = self._format_context_response(response)
        
        return AgentMessage(
            sender=self.role,
            recipient=AgentRole.EXECUTIVE_AGENT,
            content=context_summary,
            context={
                "paths": [p.explanation for p in response.paths],
                "operational_context": response.operational_context,
                "analytical_context": response.analytical_context,
                "sources": response.sources_used,
                "confidence": response.confidence_score
            }
        )
        
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from natural language query"""
        # Simple keyword extraction (would use LLM/NER in production)
        entities = {"start": [], "end": []}
        
        # Look for customer references
        if "acme" in query.lower():
            entities["start"].append("cust_acme")
        if "globex" in query.lower():
            entities["start"].append("cust_globex")
            
        # Look for decision makers
        if "vp" in query.lower() or "approval" in query.lower():
            entities["end"].append("vp_sales")
        if "discount" in query.lower():
            entities["end"].append("deal_001")
            
        return entities
        
    def _format_context_response(self, response: AgentResponse) -> str:
        """Format the response for downstream agents"""
        parts = []
        
        parts.append(f"=== Context Graph Query Results ===")
        parts.append(f"Found {len(response.paths)} relevant decision paths.")
        parts.append("")
        
        # Add path information
        for i, path in enumerate(response.paths, 1):
            parts.append(f"Path {i}:")
            parts.append(path.explanation or "No explanation available")
            parts.append("")
            
        # Add context summary
        if response.operational_context:
            parts.append("Relevant Policies/SOPs:")
            for ctx in response.operational_context:
                parts.append(f"  - {ctx['id']}")
                
        if response.analytical_context:
            parts.append("\nRelevant Metrics/Definitions:")
            for ctx in response.analytical_context:
                parts.append(f"  - {ctx['id']}")
                
        parts.append(f"\nSources: {', '.join(response.sources_used)}")
        parts.append(f"Confidence: {response.confidence_score:.2%}")
        
        return "\n".join(parts)


class ExecutiveAgent(BaseAgent):
    """
    Agent that interprets hypergraph paths mechanistically.
    
    Analogous to Engineer in the paper:
    - Receives subgraph from ContextAgent
    - Interprets the mechanistic relationships
    - Synthesizes explanation
    """
    
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.EXECUTIVE_AGENT, llm_client)
        
    def _build_system_prompt(self) -> str:
        return """You are an Executive Agent responsible for interpreting 
decision context mechanistically.

Your role:
1. Receive context from the Context Agent (hypergraph paths, policies, metrics)
2. Interpret HOW different events are connected
3. Identify the causal chain of decisions
4. Synthesize a clear explanation of the decision rationale

When interpreting paths:
- Focus on the intersection nodes (bridging entities)
- Explain WHY each decision led to the next
- Reference specific policies and metrics
- Identify any precedents that apply

Your output should be a clear, mechanistic explanation that a human 
could use to understand the decision-making process."""

    def process(self, message: AgentMessage) -> AgentMessage:
        """Interpret context and generate explanation"""
        context = message.context
        
        # Generate mechanistic interpretation
        interpretation = self._interpret_paths(
            context.get("paths", []),
            context.get("operational_context", []),
            context.get("analytical_context", [])
        )
        
        return AgentMessage(
            sender=self.role,
            recipient=AgentRole.GOVERNANCE_AGENT,
            content=interpretation,
            context={
                **context,
                "interpretation": interpretation
            }
        )
        
    def _interpret_paths(
        self,
        paths: List[str],
        operational: List[Dict],
        analytical: List[Dict]
    ) -> str:
        """Generate mechanistic interpretation of paths"""
        parts = []
        
        parts.append("=== Mechanistic Interpretation ===")
        parts.append("")
        
        # Would use LLM for sophisticated interpretation
        # For demo, provide structured analysis
        
        if paths:
            parts.append("Decision Chain Analysis:")
            for i, path_explanation in enumerate(paths, 1):
                parts.append(f"\nChain {i}:")
                parts.append(path_explanation)
                parts.append("  Interpretation: The entities in this chain are connected")
                parts.append("  through shared decision events, indicating direct influence.")
                
        # Interpret operational context
        if operational:
            parts.append("\n\nPolicy Alignment:")
            for ctx in operational:
                parts.append(f"  - {ctx['id']}: This policy was referenced in the decision chain,")
                parts.append("    indicating the decision followed established procedures.")
                
        # Interpret analytical context
        if analytical:
            parts.append("\n\nMetric Influence:")
            for ctx in analytical:
                parts.append(f"  - {ctx['id']}: This metric informed the decision,")
                parts.append("    providing quantitative justification.")
                
        parts.append("\n\nConclusion:")
        parts.append("The decision trace shows a clear mechanistic path from")
        parts.append("the triggering event through the approval chain, with")
        parts.append("appropriate policy and metric references.")
        
        return "\n".join(parts)


class GovernanceAgent(BaseAgent):
    """
    Agent that ensures compliance and proposes actions.
    
    Analogous to Hypothesizer in the paper:
    - Receives interpretation from ExecutiveAgent
    - Verifies compliance with policies
    - Proposes recommended actions
    - Identifies governance risks
    
    Key insight from blog: "Enterprises will want to own their own context
    with open, federated context platforms that any agent can read from,
    humans can govern, and the organization can improve over time."
    """
    
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.GOVERNANCE_AGENT, llm_client)
        
    def _build_system_prompt(self) -> str:
        return """You are a Governance Agent responsible for ensuring 
compliance and proposing actions.

Your role:
1. Receive interpretation from the Executive Agent
2. Verify the decision aligns with company policies
3. Check for any governance risks or compliance issues
4. Propose recommended actions based on precedents
5. Flag any items requiring human review

When reviewing decisions:
- Check if proper approval chains were followed
- Verify metrics used are current and accurate
- Ensure no exceptions were granted without justification
- Compare with historical precedents

Your output should include:
1. Compliance assessment (compliant/review needed/non-compliant)
2. Risk factors identified
3. Recommended actions
4. Items for human review (if any)"""

    def process(self, message: AgentMessage) -> AgentMessage:
        """Review for compliance and propose actions"""
        context = message.context
        
        # Generate governance review
        review = self._governance_review(
            message.content,
            context.get("operational_context", []),
            context.get("confidence", 0.0)
        )
        
        return AgentMessage(
            sender=self.role,
            recipient=AgentRole.SALES_AGENT,  # Return to requesting agent
            content=review,
            context={
                **context,
                "governance_review": review
            }
        )
        
    def _governance_review(
        self,
        interpretation: str,
        operational: List[Dict],
        confidence: float
    ) -> str:
        """Generate governance review and recommendations"""
        parts = []
        
        parts.append("=== Governance Review ===")
        parts.append("")
        
        # Compliance assessment
        parts.append("Compliance Status: COMPLIANT")
        parts.append("  - Decision follows established approval chain")
        parts.append("  - Relevant policies were referenced")
        parts.append("  - Precedent exists for similar decisions")
        
        # Risk factors
        parts.append("\nRisk Factors:")
        if confidence < 0.5:
            parts.append("  ⚠️ LOW CONFIDENCE: Limited context available")
        else:
            parts.append("  ✓ Adequate context and documentation")
            
        if not operational:
            parts.append("  ⚠️ No policies explicitly referenced")
        else:
            parts.append("  ✓ Policies properly referenced")
            
        # Recommended actions
        parts.append("\nRecommended Actions:")
        parts.append("  1. Document this decision as precedent for future reference")
        parts.append("  2. Update customer health score based on renewal outcome")
        parts.append("  3. Schedule 30-day check-in to verify customer satisfaction")
        
        # Human review items
        parts.append("\nItems for Human Review:")
        parts.append("  - None required at this time")
        
        # Feedback loop recommendation
        parts.append("\nFeedback Loop:")
        parts.append("  This decision should be tracked for outcome analysis.")
        parts.append("  If successful, strengthen the connection between incident")
        parts.append("  history and discount justification in the context graph.")
        
        return "\n".join(parts)


class EnterpriseReasoningSystem:
    """
    Orchestrates multi-agent reasoning over the enterprise context graph.
    
    This is the main entry point for enterprise decision support.
    
    From blog: "Context compounds through feedback loops"
    - Accuracy creates trust
    - Trust creates adoption  
    - Adoption creates feedback
    - Feedback creates accuracy
    """
    
    def __init__(self, query_engine: ContextGraphQueryEngine, llm_client=None):
        self.query_engine = query_engine
        
        # Initialize agents
        self.context_agent = ContextAgent(query_engine, llm_client)
        self.executive_agent = ExecutiveAgent(llm_client)
        self.governance_agent = GovernanceAgent(llm_client)
        
        # Conversation log for the feedback flywheel
        self.conversation_log: List[AgentMessage] = []
        
    def reason(self, query: str, requester: AgentRole = AgentRole.SALES_AGENT) -> Dict[str, Any]:
        """
        Execute multi-agent reasoning for a query.
        
        This mimics the dialogue flow from Figure 9 in the paper:
        User → GraphAgent → Engineer → Hypothesizer
        
        Enterprise version:
        SalesAgent → ContextAgent → ExecutiveAgent → GovernanceAgent
        """
        # Initial query from domain agent
        initial_message = AgentMessage(
            sender=requester,
            recipient=AgentRole.CONTEXT_AGENT,
            content=query,
            context={"intersection_size": 1, "k_paths": 3}
        )
        self.conversation_log.append(initial_message)
        
        # Step 1: ContextAgent finds relevant context
        context_response = self.context_agent.process(initial_message)
        self.conversation_log.append(context_response)
        
        # Step 2: ExecutiveAgent interprets mechanistically
        executive_response = self.executive_agent.process(context_response)
        self.conversation_log.append(executive_response)
        
        # Step 3: GovernanceAgent reviews and recommends
        governance_response = self.governance_agent.process(executive_response)
        self.conversation_log.append(governance_response)
        
        # Compile final response
        return {
            "query": query,
            "requester": requester.value,
            "context_summary": context_response.content,
            "interpretation": executive_response.content,
            "governance_review": governance_response.content,
            "full_context": governance_response.context,
            "conversation_log": [m.to_dict() for m in self.conversation_log]
        }
        
    def get_conversation_log(self) -> List[Dict[str, Any]]:
        """Get the full conversation log for audit/feedback"""
        return [m.to_dict() for m in self.conversation_log]


def demo_multi_agent_reasoning():
    """Demonstrate the multi-agent reasoning system"""
    from hypergraph_builder import demo_build_enterprise_hypergraph
    
    print("=" * 60)
    print("ENTERPRISE MULTI-AGENT REASONING SYSTEM")
    print("Based on Stewart & Buehler Hypergraph Methodology")
    print("=" * 60)
    
    # Build the hypergraph
    print("\n[1/3] Building Enterprise Context Graph...")
    builder, hypergraph = demo_build_enterprise_hypergraph()
    
    # Create query engine
    print("[2/3] Initializing Query Engine...")
    query_engine = ContextGraphQueryEngine(hypergraph)
    
    # Create reasoning system
    print("[3/3] Creating Multi-Agent System...")
    reasoning_system = EnterpriseReasoningSystem(query_engine)
    
    # Execute query
    print("\n" + "=" * 60)
    print("EXECUTING QUERY")
    print("=" * 60)
    
    query = "Why was Acme Corp given a 20% discount on their renewal?"
    print(f"\nQuery: {query}")
    print("-" * 60)
    
    result = reasoning_system.reason(query)
    
    # Print results
    print("\n" + "=" * 60)
    print("CONTEXT AGENT RESPONSE")
    print("=" * 60)
    print(result["context_summary"])
    
    print("\n" + "=" * 60)
    print("EXECUTIVE AGENT INTERPRETATION")
    print("=" * 60)
    print(result["interpretation"])
    
    print("\n" + "=" * 60)
    print("GOVERNANCE AGENT REVIEW")
    print("=" * 60)
    print(result["governance_review"])
    
    return reasoning_system, result


if __name__ == "__main__":
    demo_multi_agent_reasoning()
