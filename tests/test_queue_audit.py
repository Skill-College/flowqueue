"""Unit tests for the queue timeline chokepoint (no DB)."""

import uuid

from app.services import queue_audit_service


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def test_write_queue_log_adds_one_row_with_fields():
    session = FakeSession()
    qid, aid = uuid.uuid4(), uuid.uuid4()

    log = queue_audit_service.write_queue_log(
        session,
        queue_id=qid,
        action=queue_audit_service.QUEUE_PURGED,
        actor_id=aid,
        remark="Purged 5 pending messages",
        context={"messages": 5, "deliveries": 5},
    )

    assert len(session.added) == 1
    assert session.added[0] is log
    assert log.queue_id == qid
    assert log.action == "queue_purged"
    assert log.actor_id == aid
    assert log.remark == "Purged 5 pending messages"
    assert log.context == {"messages": 5, "deliveries": 5}
    assert log.meta == {}


def test_action_constants_are_distinct():
    assert len(set(queue_audit_service.ACTIONS)) == len(queue_audit_service.ACTIONS)
    assert queue_audit_service.MESSAGES_EXPIRED in queue_audit_service.ACTIONS
