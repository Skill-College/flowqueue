"""Unit tests for retry-or-fail logic in delivery_service.apply_failure.

Uses lightweight stand-ins for Delivery/Queue/session so no DB is required.
"""

from types import SimpleNamespace

from app.models.delivery import DeliveryStatus
from app.services import delivery_service


class FakeSession:
    """Captures delivery_log rows added during a transition."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def _delivery(attempt=0):
    return SimpleNamespace(
        id="d1",
        status=DeliveryStatus.processing,
        attempt_count=attempt,
        visible_after=None,
        last_remark=None,
        meta={},
        completed_at=None,
    )


def _queue(max_retries=3, retry_delay=60):
    return SimpleNamespace(max_retries=max_retries, retry_delay_seconds=retry_delay)


def test_retry_scheduled_when_attempts_remain():
    session, d, q = FakeSession(), _delivery(attempt=0), _queue(max_retries=3)
    delivery_service.apply_failure(session, d, q, remark="boom")
    assert d.attempt_count == 1
    assert d.status == DeliveryStatus.pending
    assert d.visible_after is not None
    log = session.added[-1]
    assert log.event_type == "retry_scheduled"
    assert log.to_status == "pending"


def test_marked_failed_when_retries_exhausted():
    session, d, q = FakeSession(), _delivery(attempt=2), _queue(max_retries=3)
    delivery_service.apply_failure(session, d, q, remark="boom")
    assert d.attempt_count == 3
    assert d.status == DeliveryStatus.failed
    log = session.added[-1]
    assert log.event_type == "status_updated"
    assert log.to_status == "failed"


def test_every_failure_writes_exactly_one_log():
    session, d, q = FakeSession(), _delivery(attempt=0), _queue()
    delivery_service.apply_failure(session, d, q, remark="x")
    assert len(session.added) == 1
