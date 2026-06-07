"""SDK tests using httpx MockTransport (no live server)."""

import httpx
import pytest

from flowqueue import ApiError, FlowQueueClient
from flowqueue.consumer import FlowQueueConsumer


def make_client(handler) -> FlowQueueClient:
    client = FlowQueueClient("http://test", "fq_key")
    client._http = httpx.Client(
        base_url="http://test",
        headers={"Authorization": "Bearer fq_key"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_publish_scheduled_sends_delay_and_auth():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("Authorization")
        import json

        seen["body"] = json.loads(req.content)
        return httpx.Response(201, json={"id": "m1", "sequence_num": 1})

    c = make_client(handler)
    out = c.publish("q1", {"a": 1}, idempotency_key="k", delay_seconds=30)
    assert out["id"] == "m1"
    assert seen["url"].endswith("/api/v1/queues/q1/messages")
    assert seen["auth"] == "Bearer fq_key"
    assert seen["body"] == {"payload": {"a": 1}, "idempotency_key": "k", "delay_seconds": 30}


def test_api_error_parses_envelope():
    def handler(req):
        return httpx.Response(409, json={"error": {"code": "conflict", "message": "nope"}})

    c = make_client(handler)
    with pytest.raises(ApiError) as ei:
        c.publish("q1", {"a": 1})
    assert ei.value.status == 409
    assert ei.value.code == "conflict"


def test_poll_none_on_204():
    c = make_client(lambda req: httpx.Response(204))
    assert FlowQueueConsumer(c, "c1").poll() is None


def test_consumer_run_completes_then_stops():
    calls = {"poll": 0, "complete": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/poll"):
            calls["poll"] += 1
            if calls["poll"] == 1:
                return httpx.Response(200, json={
                    "id": "d1", "message_id": "m1", "consumer_id": "c1",
                    "status": "processing", "attempt_count": 0,
                    "payload": {"x": 1}, "sequence_num": 1,
                })
            return httpx.Response(204)
        if req.url.path.endswith("/complete"):
            calls["complete"] += 1
            return httpx.Response(200, json={"status": "completed"})
        return httpx.Response(200, json={})

    c = make_client(handler)
    got = []
    FlowQueueConsumer(c, "c1").run(lambda d: got.append(d.payload), poll_interval=0, max_iterations=2)
    assert got == [{"x": 1}]
    assert calls["complete"] == 1


def test_dlq_and_replay_paths():
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path))
        return httpx.Response(200, json={})

    c = make_client(handler)
    c.dlq_list("q1")
    c.requeue("d1")
    c.replay_failed("c1")
    paths = [p for _, p in seen]
    assert "/api/v1/queues/q1/dlq" in paths
    assert "/api/v1/deliveries/d1/requeue" in paths
    assert "/api/v1/consumers/c1/replay/failed" in paths
