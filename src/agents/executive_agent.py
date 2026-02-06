"""Executive Agent - reasoning and interpretation.

Operates on 2-morphisms: proposes arrows between arrows (meta-relations).
Types include PRECEDENT, EXCEPTION, GENERALIZATION.

From Higher-Order Reasoning PDF Section 3:
The Hypothesizer proposes 2-cells - typed connections between decisions.
"""

from __future__ import annotations

from src.agents.base import AgentQuery, AgentResponse, BaseAgent
from src.llm.base import BaseLLMConnector


class ExecutiveAgent(BaseAgent):
    """Agent for mechanistic interpretation and causal reasoning.

    Capabilities:
    - Causal chain construction from hypergraph paths
    - Decision rationale synthesis
    - 2-morphism proposal (precedent/exception identification)
    """

    def __init__(self, llm: BaseLLMConnector | None = None) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return "executive_agent"

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Synthesize reasoning from context paths.

        Takes paths found by the ContextAgent and produces
        mechanistic interpretations and decision rationale.
        """
        paths = query.context.get("paths", [])
        entities = query.context.get("entities", [])

        if not paths and not entities:
            return AgentResponse(
                answer="No context paths or entities provided for reasoning.",
                confidence=0.0,
            )

        # If LLM is available, use it for reasoning
        if self._llm:
            prompt = self._build_reasoning_prompt(query.query, paths, entities)
            answer = await self._llm.complete(
                prompt=prompt,
                system_prompt=(
                    "You are an executive reasoning agent. Analyze decision "
                    "traces and construct causal chains explaining how "
                    "enterprise decisions were made."
                ),
            )
            return AgentResponse(
                answer=answer,
                evidence=[{"paths": paths, "entities": entities}],
                paths_found=len(paths),
                confidence=0.8,
            )

        # Without LLM, return structured summary
        return AgentResponse(
            answer=f"Found {len(paths)} decision path(s) involving "
                   f"{len(entities)} entities. LLM required for full reasoning.",
            evidence=[{"paths": paths, "entities": entities}],
            paths_found=len(paths),
            confidence=0.3,
        )

    @staticmethod
    def _build_reasoning_prompt(
        query: str,
        paths: list[object],
        entities: list[object],
    ) -> str:
        """Build the reasoning prompt for the LLM."""
        return f"""Analyze the following enterprise decision context and answer the query.

Query: {query}

Decision Paths Found: {len(paths)}
Entities Involved: {len(entities)}

Paths: {paths}
Entities: {entities}

Provide:
1. A mechanistic interpretation of how the decision was made
2. The causal chain from context to outcome
3. Any precedents or exceptions identified
4. Confidence assessment of the reasoning
"""
