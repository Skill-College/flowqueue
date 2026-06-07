"""Unit tests for the deterministic filter rule engine."""

from app.core.routing_engine import extract_field, matches


def test_extract_field_dot_notation():
    data = {"payload": {"country": "IN", "nested": {"amount": 10}}}
    assert extract_field(data, "payload.country") == "IN"
    assert extract_field(data, "payload.nested.amount") == 10
    assert extract_field(data, "payload.missing") is None


def test_no_rules_always_delivers():
    assert matches([], {"anything": 1}) is True


def test_equals_match():
    rules = [{"field": "payload.country", "operator": "equals", "value": "IN"}]
    assert matches(rules, {"country": "IN"}) is True
    assert matches(rules, {"country": "US"}) is False


def test_mode_any_vs_all():
    rules = [
        {"field": "payload.country", "operator": "equals", "value": "IN"},
        {"field": "payload.amount", "operator": "greater_than", "value": 1000},
    ]
    # any: one match is enough
    assert matches(rules, {"country": "IN", "amount": 5}, "any") is True
    # all: both must match
    assert matches(rules, {"country": "IN", "amount": 5}, "all") is False
    assert matches(rules, {"country": "IN", "amount": 1500}, "all") is True
    # any: neither matches
    assert matches(rules, {"country": "US", "amount": 5}, "any") is False


def test_greater_than_numeric_only():
    rules = [{"field": "payload.amount", "operator": "greater_than", "value": 1000}]
    assert matches(rules, {"amount": 1500}) is True
    assert matches(rules, {"amount": 500}) is False
    assert matches(rules, {"amount": "lots"}) is False  # non-numeric => no crash


def test_contains():
    rules = [{"field": "payload.tags", "operator": "contains", "value": "vip"}]
    assert matches(rules, {"tags": ["a", "vip"]}) is True
    assert matches(rules, {"tags": ["a"]}) is False


def test_malformed_rules_do_not_block():
    rules = [{"field": "payload.x", "operator": "bogus", "value": 1}]
    assert matches(rules, {"x": 1}) is True  # no usable rules => deliver
