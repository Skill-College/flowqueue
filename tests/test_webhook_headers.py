"""Unit tests for webhook custom headers + reserved-header precedence (no DB)."""

import hashlib
import hmac
from types import SimpleNamespace

from app.services import webhook_service


class FakeResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class FakeClient:
    """Captures the headers passed to .post for assertions."""

    def __init__(self):
        self.captured = None

    async def post(self, url, content=None, headers=None, timeout=None):
        self.captured = {"url": url, "content": content, "headers": headers}
        return FakeResponse()


def _consumer(**kw):
    base = dict(
        endpoint_url="https://hooks.example.com/in",
        signing_secret=None,
        custom_headers={},
    )
    base.update(kw)
    return SimpleNamespace(**base)


async def test_custom_headers_are_sent(monkeypatch):
    monkeypatch.setattr(webhook_service, "validate_endpoint_url", lambda url: None)
    client = FakeClient()
    consumer = _consumer(custom_headers={"X-Api-Key": "secret", "X-Tenant": "acme"})

    result = await webhook_service._post(
        client, consumer, {"a": 1}, {"X-FlowQueue-Event": "test"}
    )

    assert result.success is True
    h = client.captured["headers"]
    assert h["X-Api-Key"] == "secret"
    assert h["X-Tenant"] == "acme"
    assert h["Content-Type"] == "application/json"
    assert h["X-FlowQueue-Event"] == "test"


async def test_reserved_headers_win_over_custom(monkeypatch):
    monkeypatch.setattr(webhook_service, "validate_endpoint_url", lambda url: None)
    client = FakeClient()
    # Caller tries to override reserved + content-type; both must be ignored.
    consumer = _consumer(
        custom_headers={
            "X-FlowQueue-Event": "forged",
            "Content-Type": "text/plain",
            "X-Api-Key": "ok",
        }
    )

    await webhook_service._post(
        client, consumer, {"a": 1}, {"X-FlowQueue-Event": "real"}
    )

    h = client.captured["headers"]
    assert h["X-FlowQueue-Event"] == "real"  # reserved base header wins
    assert h["Content-Type"] == "application/json"  # we always set JSON
    assert h["X-Api-Key"] == "ok"  # non-reserved custom header preserved


async def test_signature_still_applied_with_custom_headers(monkeypatch):
    monkeypatch.setattr(webhook_service, "validate_endpoint_url", lambda url: None)
    client = FakeClient()
    consumer = _consumer(signing_secret="s3cr3t", custom_headers={"X-Api-Key": "ok"})

    await webhook_service._post(client, consumer, {"a": 1}, {})

    h = client.captured["headers"]
    body = client.captured["content"]
    expected = "sha256=" + hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert h["X-FlowQueue-Signature"] == expected
    assert h["X-Api-Key"] == "ok"
