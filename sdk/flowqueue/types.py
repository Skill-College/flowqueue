"""Typed response shapes for the FlowQueue SDK.

Responses stay plain dicts at runtime; these TypedDicts give editors full key
autocomplete and type checking. Optional keys use total=False sub-dicts merged via
inheritance (no typing_extensions / NotRequired needed — keeps Python 3.9 compat).
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional, TypedDict

JSON = Dict[str, Any]

DeliveryStatus = Literal["pending", "processing", "completed", "failed", "dead"]


class MessageOut(TypedDict):
    """A published message (returned by publish)."""

    id: str
    queue_id: str
    payload: JSON
    idempotency_key: Optional[str]
    sequence_num: int
    published_at: str
    scheduled_for: Optional[str]
    expires_at: str


class _DeliveryRequired(TypedDict):
    id: str
    message_id: str
    consumer_id: str
    status: DeliveryStatus
    attempt_count: int


class DeliveryOut(_DeliveryRequired, total=False):
    """A delivery returned by poll/ack/complete/fail/add_remark.

    The poll endpoint includes the message `payload` and `sequence_num`; lifecycle
    endpoints may omit them — hence these keys are optional.
    """

    payload: JSON
    sequence_num: int
    visible_after: Optional[str]
    last_remark: Optional[str]
    metadata: JSON
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]


__all__ = ["JSON", "DeliveryStatus", "MessageOut", "DeliveryOut"]
