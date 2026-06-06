"""Webhook service — HTTP delivery of payloads to webhook/workflow consumers.

Resolves the target URL via the routing engine, POSTs the payload with FlowQueue
headers, and classifies the response. The dispatcher worker calls deliver() then
records the lifecycle transition (which writes the delivery_log).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.routing_engine import evaluate
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


def resolve_target_url(consumer: Consumer, payload: dict) -> str | None:
    """Pick the destination URL: first matching routing rule, else endpoint_url."""
    routed = evaluate(consumer.routing_rules or [], payload)
    return routed or consumer.endpoint_url


async def deliver(
    client: httpx.AsyncClient,
    consumer: Consumer,
    delivery: Delivery,
    message: Message,
) -> WebhookResult:
    """POST the message payload to the consumer's resolved target URL.

    Sends headers X-FlowQueue-Delivery-ID, X-FlowQueue-Message-ID,
    X-FlowQueue-Timestamp. Re-validates the URL for SSRF at dispatch time.
    2xx => success. Does NOT mutate the delivery or write logs (caller does).
    """
    target = resolve_target_url(consumer, message.payload)
    if not target:
        return WebhookResult(False, None, None, "No target URL resolved")

    try:
        validate_endpoint_url(target)
    except Exception as exc:  # SSRFError
        return WebhookResult(False, None, target, f"Blocked target: {exc}")

    headers = {
        "Content-Type": "application/json",
        "X-FlowQueue-Delivery-ID": str(delivery.id),
        "X-FlowQueue-Message-ID": str(message.id),
        "X-FlowQueue-Timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = await client.post(target, json=message.payload, headers=headers, timeout=15.0)
    except httpx.HTTPError as exc:
        return WebhookResult(False, None, target, f"HTTP error: {exc}")

    ok = 200 <= resp.status_code < 300
    return WebhookResult(ok, resp.status_code, target, None if ok else resp.text[:500])
