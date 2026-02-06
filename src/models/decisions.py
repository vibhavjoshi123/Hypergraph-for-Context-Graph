"""Decision trace and 2-morphism models.

2-morphisms capture relationships BETWEEN hyperedges (decisions):
- Precedent: Decision B cited Decision A as precedent
- Override: Decision B overrides Decision A
- Generalization: Decision B generalizes from Decision A

From the Higher-Order Reasoning PDF:
- 1-morphisms = hyperedges (relations between entities)
- 2-morphisms = meta-relations (relations between relations)
- Coherence = diagram commutativity (logical consistency of chains)

TypeDB implements these via nested relations (relations playing roles
in other relations).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TwoMorphismType(StrEnum):
    """Types of 2-morphisms (meta-relations between decisions).

    From the Chemical Reaction Networks PDF Table 6:
    - SEQUENCE: Elementary step follows another
    - PRECEDENT: Pathway establishes reaction pattern
    - OVERRIDE: Competing pathway dominates
    - GENERALIZATION: Mechanism class abstracts cases
    """

    SEQUENCE = "sequence"
    PRECEDENT = "precedent"
    OVERRIDE = "override"
    GENERALIZATION = "generalization"
    EXCEPTION = "exception"
    JUSTIFICATION = "justification"


class PrecedentChain(BaseModel):
    """A 2-morphism linking two decision hyperedges.

    Maps to TypeDB's nested relation: `precedent-chain` where
    discount-approval relations play roles in this meta-relation.

    Example: Decision B (25% discount) cites Decision A (20% discount)
    as precedent via alpha: A -> B.
    """

    precedent_id: str = Field(..., description="ID of the earlier decision (source)")
    derived_id: str = Field(..., description="ID of the later decision (target)")
    morphism_type: TwoMorphismType = Field(default=TwoMorphismType.PRECEDENT)
    rationale: str | None = Field(default=None, description="Why this precedent applies")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExceptionOverride(BaseModel):
    """An exception override 2-morphism.

    Models the catalyst-approver isomorphism from the Chemical Reaction
    Networks PDF: an approver bypasses a policy threshold, analogous to
    a catalyst lowering activation energy.
    """

    base_decision_id: str = Field(..., description="Original decision being overridden")
    exception_decision_id: str = Field(..., description="Exception decision")
    override_rationale: str | None = None
    approver_id: str | None = Field(
        default=None, description="Entity ID of the approver (the 'catalyst')"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DecisionTrace(BaseModel):
    """A complete decision trace with coherence information.

    From the Higher-Order Reasoning PDF Section 4:
    The coherence diagram checks if beta = alpha . gamma
    (the triangle commutes). This validates that reasoning chains
    are logically consistent.
    """

    trace_id: str
    decisions: list[str] = Field(..., description="Ordered list of decision hyperedge IDs")
    two_morphisms: list[PrecedentChain] = Field(default_factory=list)
    overrides: list[ExceptionOverride] = Field(default_factory=list)
    is_coherent: bool | None = Field(
        default=None, description="Whether the trace passes coherence verification"
    )
    coherence_violations: list[str] = Field(
        default_factory=list, description="Descriptions of coherence violations"
    )
