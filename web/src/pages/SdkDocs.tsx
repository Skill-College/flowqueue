import { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { copy } from "@/lib/utils";

function Code({ code }: { code: string }) {
  const [done, setDone] = useState(false);
  return (
    <div className="relative">
      <pre className="max-h-[28rem] overflow-auto rounded-lg border border-border bg-background/60 p-3 pr-10 text-xs leading-relaxed">
        <code>{code}</code>
      </pre>
      <Button
        size="icon"
        variant="ghost"
        className="absolute right-2 top-2 h-7 w-7"
        onClick={async () => {
          await copy(code);
          setDone(true);
          setTimeout(() => setDone(false), 1200);
        }}
      >
        {done ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
      </Button>
    </div>
  );
}

export function SdkDocs() {
  const base = window.location.origin;
  return (
    <div>
      <PageHeader
        title="Python SDK"
        description="Official flowqueue client — async, typed, publish + consume"
        action={
          <a href="https://pypi.org/project/flowqueue/" target="_blank" rel="noreferrer">
            <Button variant="outline">
              PyPI <ExternalLink size={14} />
            </Button>
          </a>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardHeader><CardTitle>Install</CardTitle></CardHeader>
          <CardContent>
            <Code code={`pip install flowqueue   # async, typed; Python 3.9+`} />
            <p className="mt-3 text-sm text-muted-foreground">
              The SDK is runtime-only: <strong>publish</strong> and <strong>consume</strong>.
              Create queues, consumers and API keys in this dashboard.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Quickstart</CardTitle></CardHeader>
          <CardContent>
            <Code code={`import asyncio
from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

# create the queue + consumer in the dashboard, then use their ids
QUEUE_ID = "<queue_id>"
CONSUMER_ID = "<consumer_id>"

async def main():
    async with AsyncFlowQueueClient("${base}", "fq_your_api_key") as client:
        # Publish
        await client.publish(QUEUE_ID, {"order_id": 42}, idempotency_key="order-42")

        # Consume one delivery
        c = AsyncFlowQueueConsumer(client, CONSUMER_ID)
        d = await c.poll()
        if d:
            print(d["payload"])
            await c.complete(d["id"], remark="done")

asyncio.run(main())`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Producer — publish & schedule</CardTitle></CardHeader>
          <CardContent>
            <Code code={`# immediate
await client.publish(qid, {"hello": "world"})

# idempotent (dedup by key)
await client.publish(qid, {"hello": "world"}, idempotency_key="evt-123")

# delayed delivery (seconds)
await client.publish(qid, {"ping": 1}, delay_seconds=30)

# scheduled for an absolute time
from datetime import datetime, timedelta, timezone
await client.publish(qid, {"ping": 1}, deliver_at=datetime.now(timezone.utc) + timedelta(hours=1))`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Consumer — worker loop</CardTitle></CardHeader>
          <CardContent>
            <Code code={`import asyncio
from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

async def handle(delivery):
    # return normally -> delivery completed
    # raise -> delivery failed (retry, then dead-letter per queue config)
    await process(delivery["payload"])

async def main():
    async with AsyncFlowQueueClient("${base}", "fq_your_api_key") as client:
        consumer = AsyncFlowQueueConsumer(client, "<consumer_id>")
        await consumer.run(handle, poll_interval=2.0)

asyncio.run(main())`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Errors</CardTitle></CardHeader>
          <CardContent>
            <Code code={`from flowqueue import ApiError

try:
    await client.publish(qid, {"x": 1})
except ApiError as e:
    print(e.status, e.code, e.message)`} />
            <p className="mt-3 text-sm text-muted-foreground">
              Management, replay & DLQ live in this dashboard. Full HTTP API reference:{" "}
              <a href="/docs" className="text-primary hover:underline">/docs</a> (OpenAPI).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
