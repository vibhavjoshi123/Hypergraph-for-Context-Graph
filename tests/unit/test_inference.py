"""Tests for TypeDB inference rule management."""

from src.typedb.inference import BUILT_IN_RULES, InferenceManager, InferenceRule


class TestInferenceRule:
    def test_to_typeql(self):
        rule = InferenceRule(
            name="test-rule",
            when='$x isa customer, has health-score $hs; $hs < 50.0;',
            then='$x has tier "critical";',
        )
        typeql = rule.to_typeql()
        assert "rule test-rule:" in typeql
        assert "when" in typeql
        assert "then" in typeql

    def test_built_in_rules(self):
        assert len(BUILT_IN_RULES) >= 1
        assert BUILT_IN_RULES[0].name == "customer-at-risk"


class TestInferenceManager:
    def test_register_rule(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        rule = InferenceRule(
            name="new-rule",
            when='$d isa deal, has deal-value $v; $v > 500000.0;',
            then='$d has stage "review";',
        )
        mgr.register_rule(rule)
        assert "new-rule" in mgr.rules

    def test_unregister_rule(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        removed = mgr.unregister_rule("customer-at-risk")
        assert removed is not None
        assert "customer-at-risk" not in mgr.rules

    def test_get_rule(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        rule = mgr.get_rule("customer-at-risk")
        assert rule is not None
        assert rule.name == "customer-at-risk"

    def test_list_rules(self):
        class MockClient:
            is_connected = False

        mgr = InferenceManager(MockClient())
        rules = mgr.list_rules()
        assert len(rules) >= 1
