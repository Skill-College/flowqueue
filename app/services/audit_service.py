"""Audit service — the single chokepoint for writing the delivery_logs trail.

AUDIT INTEGRITY RULE (non-negotiable): every delivery state transition MUST write
a delivery_log row in the SAME transaction/session as the change. All delivery
mutations route through write_log() below, never inserting DeliveryLog directly.
delivery_logs are APPEND-ONLY: this module only ever adds rows.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_log import DeliveryLog

# Canonical event types (kept here for reference / validation).
EVENT_CREATED = "created"
EVENT_ACKNOWLEDGED = "acknowledged"
EVENT_STATUS_UPDATED = "status_updated"
EVENT_RETRY_SCHEDULED = "retry_scheduled"
EVENT_REPLAYED = "replayed"
EVENT_REMARK_ADDED = "remark_added"
EVENT_METADATA_UPDATED = "metadata_updated"
EVENT_EXPIRED = "expired"
EVENT_DEAD_LETTERED = "dead_lettered"
EVENT_REQUEUED = "requeued"
EVENT_DISCARDED = "discarded"


def write_log(
    session: AsyncSession,
    *,
    delivery_id: uuid.UUID,
    event_type: str,
    from_status: DeliveryStatus | str | None = None,
    to_status: DeliveryStatus | str | None = None,
    remark: str | None = None,
    meta: dict | None = None,
    context: dict | None = None,
) -> DeliveryLog:
    """Append one delivery_log row to the given session (NOT committed here).

    Caller commits as part of the surrounding transaction so the log and the
    state change land atomically. Returns the (pending) DeliveryLog instance.

    Writes to audit log: exactly this one row.
    """

    def _name(s: DeliveryStatus | str | None) -> str | None:
        if s is None:
            return None
        return s.value if isinstance(s, DeliveryStatus) else str(s)

    log = DeliveryLog(
        delivery_id=delivery_id,
        event_type=event_type,
        from_status=_name(from_status),
        to_status=_name(to_status),
        remark=remark,
        meta=meta or {},
        context=context or {},
    )
    session.add(log)
    return log


def log_transition(
    session: AsyncSession,
    delivery: Delivery,
    *,
    event_type: str,
    to_status: DeliveryStatus | str | None = None,
    remark: str | None = None,
    meta: dict | None = None,
    context: dict | None = None,
) -> DeliveryLog:
    """Convenience wrapper recording a transition off the delivery's CURRENT status.

    Pass the delivery BEFORE mutating its status so from_status is captured correctly.

    Writes to audit log: one row describing delivery.status -> to_status.
    """
    return write_log(
        session,
        delivery_id=delivery.id,
        event_type=event_type,
        from_status=delivery.status,
        to_status=to_status,
        remark=remark,
        meta=meta,
        context=context,
    )
