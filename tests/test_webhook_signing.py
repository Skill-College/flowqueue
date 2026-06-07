"""Unit tests for webhook HMAC signing + filter gating."""

import hashlib
import hmac
from types import SimpleNamespace

from app.services import webhook_service


def test_sign_body_matches_hmac_sha256():
    secret = "s3cr3t"
    body = b'{"a":1}'
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert webhook_service.sign_body(secret, body) == expected


def test_serialize_is_deterministic():
    a = webhook_service._serialize({"b": 2, "a": 1})
    b = webhook_service._serialize({"a": 1, "b": 2})
    assert a == b  # sort_keys => stable signing input


def test_should_deliver_respects_rules():
    c = SimpleNamespace(
        routing_rules=[{"field": "payload.x", "operator": "equals", "value": 1}],
        match_mode="any",
    )
    assert webhook_service.should_deliver(c, {"x": 1}) is True
    assert webhook_service.should_deliver(c, {"x": 2}) is False
    c_norules = SimpleNamespace(routing_rules=[], match_mode="any")
    assert webhook_service.should_deliver(c_norules, {"anything": 1}) is True
