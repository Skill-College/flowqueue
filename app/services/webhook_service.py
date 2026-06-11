"""Webhook service — HTTP delivery of payloads to webhook consumers.

POSTs the payload to the consumer's single endpoint_url with FlowQueue headers and
classifies the response. `should_deliver()` applies the consumer's filter rules. The
dispatcher worker calls these then records the lifecycle transition (writes the log).
"""

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.routing_engine import matches
from app.core.security import validate_endpoint_url
from app.models.consumer import Consumer
from app.models.delivery import Delivery
from app.models.message import Message


@dataclass
class WebhookResult:
    success: bool
    status_code: int | None
    target_url: str | None
    detail: str | None


def should_deliver(consumer: Consumer, payload: dict) -> bool:
    """Apply the consumer's filter rules. True => POST; False => skip (filtered)."""
    return matches(consumer.routing_rules or [], payload, consumer.match_mode)


def _serialize(payload: dict) -> bytes:
    """Canonical JSON bytes that are both sent and signed (so signatures verify)."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def sign_body(secret: str, body: bytes) -> str:
    """HMAC-SHA256 signature header value: 'sha256=<hex>'."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def _post(
    client: httpx.AsyncClient,
    consumer: Consumer,
    payload: dict,
    base_headers: dict,
) -> WebhookResult:
    target = consumer.endpoint_url
    if not target:
        return WebhookResult(False, None, None, "No endpoint URL configured")
    try:
        validate_endpoint_url(target)
    except Exception as exc:  # SSRFError
        return WebhookResult(False, None, target, f"Blocked target: {exc}")

    body = _serialize(payload)
    # Caller-supplied headers first, then reserved FlowQueue headers, then the
    # signature — reserved headers always win so callers can't forge our identity.
    headers = {
        **(consumer.custom_headers or {}),
        "Content-Type": "application/json",
        **base_headers,
    }
    if consumer.signing_secret:
        headers["X-FlowQueue-Signature"] = sign_body(consumer.signing_secret, body)
    try:
        resp = await client.post(target, content=body, headers=headers, timeout=15.0)
    except httpx.HTTPError as exc:
        return WebhookResult(False, None, target, f"HTTP error: {exc}")
    ok = 200 <= resp.status_code < 300
    return WebhookResult(ok, resp.status_code, target, resp.text[:1000] if resp.text else None)


async def send_test(client: httpx.AsyncClient, consumer: Consumer) -> WebhookResult:
    """POST a sample event to the consumer endpoint (no delivery row) for wiring checks."""
    return await _post(
        client,
        consumer,
        {"flowqueue": "test", "consumer_id": str(consumer.id)},
        {
            "X-FlowQueue-Event": "test",
            "X-FlowQueue-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def deliver(
    client: httpx.AsyncClient,
    consumer: Consumer,
    delivery: Delivery,
    message: Message,
) -> WebhookResult:
    """POST the message payload to the consumer's endpoint_url.

    Sends headers X-FlowQueue-Delivery-ID, X-FlowQueue-Message-ID,
    X-FlowQueue-Timestamp, and X-FlowQueue-Signature when a signing_secret is set.
    Re-validates the URL for SSRF at dispatch time. 2xx => success. Does NOT mutate
    the delivery or write logs (caller does).
    """
    return await _post(
        client,
        consumer,
        message.payload,
        {
            "X-FlowQueue-Delivery-ID": str(delivery.id),
            "X-FlowQueue-Message-ID": str(message.id),
            "X-FlowQueue-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
