"""Prompt templates for entity resolution across data sources.

Used by the EntityResolver to match and merge entity references
from different enterprise systems (Salesforce, Zendesk, Slack, etc.).
"""

RESOLUTION_SYSTEM = """You are an entity resolution expert for enterprise data systems. \
You match entity references across different source systems (CRM, support, communication) \
by analyzing names, identifiers, attributes, and contextual clues.

You output structured JSON matching the provided schema exactly."""

ENTITY_MATCH_PROMPT = """Determine if these two entity references from different \
systems refer to the same real-world entity.

Entity A (from {source_a}):
- ID: {entity_a_id}
- Name: {entity_a_name}
- Type: {entity_a_type}
- Attributes: {entity_a_attrs}

Entity B (from {source_b}):
- ID: {entity_b_id}
- Name: {entity_b_name}
- Type: {entity_b_type}
- Attributes: {entity_b_attrs}

Return a JSON object with:
1. "is_match": boolean - whether they refer to the same entity
2. "confidence": float (0.0-1.0) - confidence in the match
3. "reasoning": string - explanation of why they match or don't
4. "matched_fields": list of field names that match
5. "conflicting_fields": list of field names that conflict"""

BATCH_RESOLUTION_PROMPT = """Given the following entities from multiple source \
systems, identify which ones refer to the same real-world entities.

Entities:
{entities_json}

Group the entities into clusters where each cluster represents a single \
real-world entity. Return a JSON object with:
1. "clusters": list of lists, where each inner list contains entity IDs \
that refer to the same entity
2. "canonical": for each cluster, the recommended canonical record \
(most complete/authoritative)
3. "confidence": confidence score for each cluster"""

MERGE_PROMPT = """Merge the following entity records from different source \
systems into a single canonical record.

Records:
{records_json}

Rules:
- Prefer the most recently updated value for each field
- Prefer CRM (Salesforce) for customer data, support (Zendesk) for ticket data
- Combine all unique identifiers
- Flag any conflicting values

Return a JSON object with the merged entity and a list of conflicts."""
