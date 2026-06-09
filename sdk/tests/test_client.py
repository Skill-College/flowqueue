"""SDK tests using httpx MockTransport (no live server). Async-only client."""

import json

import httpx
import pytest

from flowqueue import ApiError, AsyncFlowQueueClient
from flowqueue.consumer import AsyncFlowQueueConsumer


def make_client(handler) -> AsyncFlowQueueClient:
    client = AsyncFlowQueueClient("http://test", "fq_key")
    client._http = httpx.AsyncClient(
        base_url="http://test",
        headers={"Authorization": "Bearer fq_key"},
        transport=httpx.MockTransport(handler),
    )
    return client


async def test_publish_scheduled_sends_delay_and_auth():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("Authorization")
        seen["body"] = json.loads(req.content)
        return httpx.Response(201, json={"id": "m1", "sequence_num": 1})

    c = make_client(handler)
    out = await c.publish("q1", {"a": 1}, idempotency_key="k", delay_seconds=30)
    assert out["id"] == "m1"
    assert seen["url"].endswith("/api/v1/queues/q1/messages")
    assert seen["auth"] == "Bearer fq_key"
    assert seen["body"] == {"payload": {"a": 1}, "idempotency_key": "k", "delay_seconds": 30}
    await c.aclose()


async def test_api_error_parses_envelope():
    def handler(req):
        return httpx.Response(409, json={"error": {"code": "conflict", "message": "nope"}})

    c = make_client(handler)
    with pytest.raises(ApiError) as ei:
        await c.publish("q1", {"a": 1})
    assert ei.value.status == 409
    assert ei.value.code == "conflict"
    await c.aclose()


async def test_poll_none_on_204():
    c = make_client(lambda req: httpx.Response(204))
    assert await AsyncFlowQueueConsumer(c, "c1").poll() is None
    await c.aclose()


async def test_consumer_run_completes_then_stops():
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
    await AsyncFlowQueueConsumer(c, "c1").run(
        lambda d: got.append(d["payload"]), poll_interval=0, max_iterations=2
    )
    assert got == [{"x": 1}]
    assert calls["complete"] == 1
    await c.aclose()


async def test_consumer_run_fails_on_exception():
    calls = {"fail": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/poll"):
            if calls.get("polled"):
                return httpx.Response(204)
            calls["polled"] = True
            return httpx.Response(200, json={
                "id": "d1", "message_id": "m1", "consumer_id": "c1",
                "status": "processing", "attempt_count": 0, "payload": {}, "sequence_num": 1,
            })
        if req.url.path.endswith("/fail"):
            calls["fail"] += 1
            return httpx.Response(200, json={"status": "failed"})
        return httpx.Response(200, json={})

    def boom(_d):
        raise RuntimeError("kaboom")

    c = make_client(handler)
    await AsyncFlowQueueConsumer(c, "c1").run(boom, poll_interval=0, max_iterations=2)
    assert calls["fail"] == 1
    await c.aclose()


async def test_async_handler_is_awaited():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/poll"):
            if seen:
                return httpx.Response(204)
            return httpx.Response(200, json={
                "id": "d1", "message_id": "m1", "consumer_id": "c1",
                "status": "processing", "attempt_count": 0, "payload": {"y": 2}, "sequence_num": 1,
            })
        return httpx.Response(200, json={})

    async def ahandler(d):
        seen.append(d["payload"])

    c = make_client(handler)
    await AsyncFlowQueueConsumer(c, "c1").run(ahandler, poll_interval=0, max_iterations=2)
    assert seen == [{"y": 2}]
    await c.aclose()
