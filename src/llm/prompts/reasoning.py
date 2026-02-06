"""Prompt templates for mechanistic reasoning and interpretation.

Used by the ExecutiveAgent to construct causal chains and decision
rationale from hypergraph traversal results.
"""

REASONING_SYSTEM = """You are an enterprise reasoning agent specializing in \
mechanistic interpretation of decision traces. You analyze hypergraph paths \
connecting enterprise entities through n-ary decision events and construct \
causal explanations.

Your analysis should:
1. Identify the causal chain from context to outcome
2. Highlight key decision points and their rationale
3. Note any precedents or exceptions in the trace
4. Assess confidence based on path connectivity and evidence strength"""

CAUSAL_CHAIN_PROMPT = """Analyze the following decision trace and construct a \
causal chain explanation.

Query: {query}

Decision Path (sequence of connected hyperedges):
{path_description}

Entities Involved:
{entities}

For each step in the chain, explain:
1. What triggered this decision step
2. Who was involved and in what role
3. What the outcome was
4. How it connects to the next step

Conclude with an overall causal narrative answering the query."""

PRECEDENT_ANALYSIS_PROMPT = """Analyze these decision events for precedent \
relationships (2-morphisms).

Current Decision:
{current_decision}

Historical Decisions:
{historical_decisions}

Identify:
1. Which historical decisions serve as precedents for the current one
2. The type of each precedent relationship:
   - PRECEDENT: Direct pattern reuse
   - EXCEPTION: Override of a standard pattern
   - GENERALIZATION: Abstract principle applied
   - SEQUENCE: Temporal/causal dependency
3. The strength and relevance of each precedent
4. Any conflicts or inconsistencies between precedents"""

INTERPRETATION_PROMPT = """Provide a mechanistic interpretation of how the \
following enterprise decision was reached.

Decision Event:
- Type: {decision_type}
- Participants: {participants}
- Rationale (if available): {rationale}

Context from Hypergraph:
- Connected entities: {connected_entities}
- Related decisions: {related_decisions}
- s-adjacent hyperedges: {s_adjacent}

Provide:
1. A step-by-step mechanism of how this decision was reached
2. The key factors that influenced the outcome
3. Alternative paths that could have been taken
4. Risk assessment of the decision"""
