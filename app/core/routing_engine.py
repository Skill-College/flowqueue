"""Deterministic rule engine — webhook delivery FILTER (not multi-URL routing).

routing_rules is a JSONB array of filter conditions on the consumer, e.g.:
    [{"field": "payload.country", "operator": "equals", "value": "IN"}]

`matches()` decides whether a payload should be delivered to the consumer's single
endpoint_url. match_mode 'any' => deliver if any rule matches; 'all' => deliver only
if every rule matches. No rules => always deliver. Dot-notation traversal, no eval.
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


def matches(rules: list[dict], payload: dict, mode: str = "any") -> bool:
    """Return True if `payload` passes the filter rules under `mode` ('any'|'all').

    No rules (or no valid rules) => True (always deliver). `payload` is wrapped as
    {"payload": payload} so rule fields like "payload.country" resolve correctly.
    """
    if not rules:
        return True
    envelope = {"payload": payload}
    results: list[bool] = []
    for rule in rules:
        operator = rule.get("operator")
        if operator not in _OPERATORS:
            continue  # skip malformed rules
        actual = extract_field(envelope, rule.get("field", ""))
        results.append(_compare(actual, operator, rule.get("value")))
    if not results:
        return True  # no usable rules => don't block delivery
    return all(results) if mode == "all" else any(results)
