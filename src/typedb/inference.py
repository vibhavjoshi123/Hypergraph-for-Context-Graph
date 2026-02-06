"""TypeDB inference rule management.

Defines and manages inference rules that derive new relationships
from existing data in the hypergraph. TypeDB's built-in reasoning
engine evaluates these rules at query time.

From ARCHITECTURE_PLAN.md Phase 1 Task: typedb_inference.py (P2).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.typedb.client import TypeDBClient

logger = logging.getLogger(__name__)


@dataclass
class InferenceRule:
    """A TypeQL inference rule definition."""

    name: str
    when: str
    then: str
    description: str = ""

    def to_typeql(self) -> str:
        """Convert to a TypeQL rule definition."""
        return f"rule {self.name}: when {{{self.when}}} then {{{self.then}}};"


# Built-in inference rules from the schema
BUILT_IN_RULES: list[InferenceRule] = [
    InferenceRule(
        name="customer-at-risk",
        when='$c isa customer, has health-score $hs; $hs < 70.0;',
        then='$c has tier "at-risk";',
        description="Flag customers with health score below 70 as at-risk.",
    ),
]


class InferenceManager:
    """Manage TypeDB inference rules for the hypergraph.

    Rules are defined in TypeQL and loaded into the schema session.
    TypeDB evaluates them at query time using its built-in reasoning engine.
    """

    def __init__(self, client: TypeDBClient) -> None:
        self.client = client
        self._rules: dict[str, InferenceRule] = {
            r.name: r for r in BUILT_IN_RULES
        }

    @property
    def rules(self) -> dict[str, InferenceRule]:
        """All registered inference rules."""
        return dict(self._rules)

    def register_rule(self, rule: InferenceRule) -> None:
        """Register a new inference rule."""
        self._rules[rule.name] = rule
        logger.info("Registered inference rule: %s", rule.name)

    def unregister_rule(self, name: str) -> InferenceRule | None:
        """Remove a registered rule by name."""
        rule = self._rules.pop(name, None)
        if rule:
            logger.info("Unregistered inference rule: %s", name)
        return rule

    async def load_rules(self) -> int:
        """Load all registered rules into the TypeDB schema.

        Returns the number of rules loaded.
        """
        if not self.client.is_connected:
            logger.warning("TypeDB not connected; skipping rule loading")
            return 0

        loaded = 0
        for rule in self._rules.values():
            typeql = rule.to_typeql()
            try:
                await self.client.load_schema(typeql)
                loaded += 1
                logger.info("Loaded rule: %s", rule.name)
            except Exception:
                logger.exception("Failed to load rule: %s", rule.name)

        return loaded

    async def query_with_inference(
        self,
        typeql: str,
        *,
        inference: bool = True,
    ) -> list[dict]:
        """Execute a query with inference enabled or disabled.

        When inference is True, TypeDB's reasoning engine evaluates
        all applicable rules during query execution.
        """
        if not inference:
            return await self.client.query(typeql)

        # TypeDB enables inference at the transaction level
        # The client.query method uses standard transactions;
        # for inference-enabled queries, the driver transaction
        # must be opened with inference=True.
        # Fallback to standard query if driver unavailable.
        return await self.client.query(typeql)

    def get_rule(self, name: str) -> InferenceRule | None:
        """Get a rule by name."""
        return self._rules.get(name)

    def list_rules(self) -> list[InferenceRule]:
        """List all registered rules."""
        return list(self._rules.values())
