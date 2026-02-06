"""Tests for prompt templates."""

from src.llm.prompts.extraction import (
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_EXTRACTION_SYSTEM,
    RELATION_IDENTIFICATION_PROMPT,
)
from src.llm.prompts.reasoning import (
    CAUSAL_CHAIN_PROMPT,
    INTERPRETATION_PROMPT,
    PRECEDENT_ANALYSIS_PROMPT,
    REASONING_SYSTEM,
)
from src.llm.prompts.resolution import (
    BATCH_RESOLUTION_PROMPT,
    ENTITY_MATCH_PROMPT,
    MERGE_PROMPT,
    RESOLUTION_SYSTEM,
)


class TestExtractionPrompts:
    def test_system_prompt_exists(self):
        assert len(ENTITY_EXTRACTION_SYSTEM) > 0
        assert "entity extraction" in ENTITY_EXTRACTION_SYSTEM.lower()

    def test_extraction_prompt_has_placeholders(self):
        assert "{source_system}" in ENTITY_EXTRACTION_PROMPT
        assert "{record_type}" in ENTITY_EXTRACTION_PROMPT
        assert "{data}" in ENTITY_EXTRACTION_PROMPT

    def test_relation_prompt_has_placeholders(self):
        assert "{entities}" in RELATION_IDENTIFICATION_PROMPT
        assert "{context}" in RELATION_IDENTIFICATION_PROMPT


class TestReasoningPrompts:
    def test_system_prompt_exists(self):
        assert len(REASONING_SYSTEM) > 0
        assert "reasoning" in REASONING_SYSTEM.lower()

    def test_causal_chain_prompt(self):
        assert "{query}" in CAUSAL_CHAIN_PROMPT
        assert "{path_description}" in CAUSAL_CHAIN_PROMPT
        assert "{entities}" in CAUSAL_CHAIN_PROMPT

    def test_precedent_prompt(self):
        assert "{current_decision}" in PRECEDENT_ANALYSIS_PROMPT
        assert "{historical_decisions}" in PRECEDENT_ANALYSIS_PROMPT

    def test_interpretation_prompt(self):
        assert "{decision_type}" in INTERPRETATION_PROMPT
        assert "{participants}" in INTERPRETATION_PROMPT


class TestResolutionPrompts:
    def test_system_prompt_exists(self):
        assert len(RESOLUTION_SYSTEM) > 0
        assert "resolution" in RESOLUTION_SYSTEM.lower()

    def test_match_prompt(self):
        assert "{source_a}" in ENTITY_MATCH_PROMPT
        assert "{entity_a_id}" in ENTITY_MATCH_PROMPT
        assert "{source_b}" in ENTITY_MATCH_PROMPT

    def test_batch_prompt(self):
        assert "{entities_json}" in BATCH_RESOLUTION_PROMPT

    def test_merge_prompt(self):
        assert "{records_json}" in MERGE_PROMPT
