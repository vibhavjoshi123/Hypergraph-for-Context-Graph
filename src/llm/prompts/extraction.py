"""Prompt templates for entity extraction.

From ARCHITECTURE_PLAN.md Section 3.4:
LLM-powered extraction of entities and relationships from raw records.
"""

ENTITY_EXTRACTION_SYSTEM = """You are an expert at entity extraction for enterprise \
decision-making systems. You identify entities (people, organizations, deals, tickets, \
policies, metrics) and their n-ary relationships from source system records.

You output structured JSON matching the provided schema exactly."""

ENTITY_EXTRACTION_PROMPT = """Extract all entities and their relationships from the \
following record.

Source System: {source_system}
Record Type: {record_type}
Data:
{data}

Return a JSON object with:
1. "entities": List of entities, each with:
   - "entity_id": Unique identifier
   - "entity_name": Human-readable name
   - "entity_type": One of [customer, employee, deal, ticket, policy, metric]
   - "attributes": Dict of type-specific attributes

2. "relationships": List of n-ary relationships, each with:
   - "relation_type": One of [decision-event, escalation, approval, renewal, incident]
   - "participants": List of objects with "entity_id" and "role"
   - "attributes": Dict with optional "rationale", "decision_type", etc.

Focus on extracting:
- People (employees, customers, contacts)
- Organizations (companies, departments)
- Objects (deals, tickets, incidents)
- Events (approvals, escalations, decisions)
- Policies/Rules referenced
"""

RELATION_IDENTIFICATION_PROMPT = """Given these entities from an enterprise system, \
identify all n-ary relationships (hyperedges) between them.

Entities:
{entities}

Context:
{context}

For each relationship, specify:
1. The type (decision-event, escalation, approval, renewal, incident)
2. ALL participating entities and their roles
3. The rationale/mechanism for the relationship

Remember: Enterprise decisions are n-ary - a single decision can involve a customer, \
deal, policy, approver, and incident simultaneously. Do NOT split into pairwise relations.
"""
