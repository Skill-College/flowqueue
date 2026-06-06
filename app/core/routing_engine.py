"""Deterministic conditional routing engine for webhook/workflow consumers.

routing_rules is a JSONB array on the consumer, e.g.:
    [{"field": "payload.country", "operator": "equals", "value": "IN",
      "action_url": "https://api-india.example.com"}]

Field paths use simple dot-notation traversal. NO eval / dynamic code execution.
First matching rule wins; if none match, callers fall back to consumer.endpoint_url.
"""

from typing import Any

_OPERATORS = ("equals", "not_equals", "contains", "greater_than", "less_than")


def extract_field(data: dict, path: str) -> Any:
    """Traverse `data` by dot-notation `path`. Returns None if any segment missing.

    The leading `payload.` segment is supported because rules are written against a
    {"payload": {...}} envelope; callers pass that envelope in.
    """
    current: Any = data
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    if operator in ("greater_than", "less_than"):
        # Only compare when both sides are real numbers (avoid str/None surprises).
        if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
            return False
        return actual > expected if operator == "greater_than" else actual < expected
    return False


def evaluate(rules: list[dict], payload: dict) -> str | None:
    """Return the action_url of the first matching rule, or None.

    `payload` is the raw message payload; it is wrapped as {"payload": payload}
    so rule fields like "payload.country" resolve correctly.
    """
    if not rules:
        return None
    envelope = {"payload": payload}
    for rule in rules:
        operator = rule.get("operator")
        if operator not in _OPERATORS:
            continue
        actual = extract_field(envelope, rule.get("field", ""))
        if _compare(actual, operator, rule.get("value")):
            return rule.get("action_url")
    return None
