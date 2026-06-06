"""Unit tests for the deterministic routing engine."""

from app.core.routing_engine import evaluate, extract_field


def test_extract_field_dot_notation():
    data = {"payload": {"country": "IN", "nested": {"amount": 10}}}
    assert extract_field(data, "payload.country") == "IN"
    assert extract_field(data, "payload.nested.amount") == 10
    assert extract_field(data, "payload.missing") is None


def test_equals_first_match_wins():
    rules = [
        {"field": "payload.country", "operator": "equals", "value": "IN",
         "action_url": "https://in.example.com"},
        {"field": "payload.country", "operator": "equals", "value": "IN",
         "action_url": "https://second.example.com"},
    ]
    assert evaluate(rules, {"country": "IN"}) == "https://in.example.com"


def test_greater_than_numeric_only():
    rules = [{"field": "payload.amount", "operator": "greater_than", "value": 1000,
              "action_url": "https://high.example.com"}]
    assert evaluate(rules, {"amount": 1500}) == "https://high.example.com"
    assert evaluate(rules, {"amount": 500}) is None
    # non-numeric actual -> no match (no crash)
    assert evaluate(rules, {"amount": "lots"}) is None


def test_contains_and_not_equals():
    rules = [{"field": "payload.tags", "operator": "contains", "value": "vip",
              "action_url": "https://vip.example.com"}]
    assert evaluate(rules, {"tags": ["a", "vip"]}) == "https://vip.example.com"
    assert evaluate(rules, {"tags": ["a"]}) is None


def test_no_rules_returns_none():
    assert evaluate([], {"anything": 1}) is None
