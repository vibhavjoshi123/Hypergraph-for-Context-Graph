"""Tests for the multi-agent reasoning system."""

import pytest

from src.agents.base import AgentQuery, AgentResponse
from src.agents.context_agent import ContextAgent
from src.agents.executive_agent import ExecutiveAgent
from src.agents.governance_agent import GovernanceAgent
from src.models.decisions import DecisionTrace, PrecedentChain
from src.models.hyperedges import Hyperedge, RoleAssignment
from src.typedb.traversal import HypergraphTraversal


def make_hyperedge(hid: str, entity_ids: list[str]) -> Hyperedge:
    return Hyperedge(
        hyperedge_id=hid,
        participants=[
            RoleAssignment(entity_id=eid, role="participant")
            for eid in entity_ids
        ],
    )


class TestContextAgent:
    @pytest.fixture
    def agent(self):
        traversal = HypergraphTraversal()
        traversal.add_hyperedges([
            make_hyperedge("h0", ["a", "b", "c"]),
            make_hyperedge("h1", ["b", "c", "d"]),
            make_hyperedge("h2", ["c", "d", "e"]),
            make_hyperedge("h3", ["x", "y", "z"]),  # disconnected
        ])
        return ContextAgent(traversal)

    @pytest.mark.asyncio
    async def test_process(self, agent):
        query = AgentQuery(query="Find context", intersection_size=2)
        response = await agent.process(query)
        assert isinstance(response, AgentResponse)
        assert response.paths_found >= 1
        assert "component" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_find_paths(self, agent):
        paths = await agent.find_paths(0, 2, k=2, s=2)
        assert len(paths) >= 1


class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_coherent_trace(self):
        agent = GovernanceAgent()
        trace = DecisionTrace(
            trace_id="t1",
            decisions=["d1", "d2"],
            two_morphisms=[
                PrecedentChain(precedent_id="d1", derived_id="d2"),
            ],
            is_coherent=True,
        )
        query = AgentQuery(
            query="Check compliance",
            context={"traces": [trace.model_dump()]},
        )
        response = await agent.process(query)
        assert response.metadata.get("compliant") is True

    @pytest.mark.asyncio
    async def test_circular_precedent_detected(self):
        agent = GovernanceAgent()
        trace = DecisionTrace(
            trace_id="t2",
            decisions=["d1", "d2"],
            two_morphisms=[
                PrecedentChain(precedent_id="d1", derived_id="d2"),
                PrecedentChain(precedent_id="d2", derived_id="d1"),
            ],
        )
        query = AgentQuery(
            query="Check compliance",
            context={"traces": [trace.model_dump()]},
        )
        response = await agent.process(query)
        assert response.metadata.get("compliant") is False
        assert "circular" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_no_traces(self):
        agent = GovernanceAgent()
        query = AgentQuery(query="Check compliance")
        response = await agent.process(query)
        assert response.confidence == 0.0


class TestExecutiveAgent:
    @pytest.mark.asyncio
    async def test_no_context(self):
        agent = ExecutiveAgent()
        query = AgentQuery(query="Why was discount given?")
        response = await agent.process(query)
        assert response.confidence == 0.0

    @pytest.mark.asyncio
    async def test_with_context_no_llm(self):
        agent = ExecutiveAgent()
        query = AgentQuery(
            query="Why was discount given?",
            context={"paths": [["d1", "d2"]], "entities": ["cust_001"]},
        )
        response = await agent.process(query)
        assert response.paths_found == 1
        assert response.confidence == 0.3  # No LLM, lower confidence
