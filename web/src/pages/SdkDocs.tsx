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
        description="Official flowqueue client — install, produce, consume, manage"
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
          <CardContent><Code code={`pip install flowqueue`} /></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Quickstart</CardTitle></CardHeader>
          <CardContent>
            <Code code={`from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("${base}", "fq_your_api_key")

# Create a queue + pull consumer
queue = client.create_queue("orders", max_retries=5, dlq_enabled=True)
consumer = client.create_consumer(queue["id"], "billing", type="http")

# Publish
client.publish(queue["id"], {"order_id": 42}, idempotency_key="order-42")

# Consume one delivery
c = FlowQueueConsumer(client, consumer["id"])
d = c.poll()
if d:
    print(d.payload)
    c.complete(d.id, remark="done")`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Producer — publish & schedule</CardTitle></CardHeader>
          <CardContent>
            <Code code={`# immediate
client.publish(qid, {"hello": "world"})

# idempotent (dedup by key)
client.publish(qid, {"hello": "world"}, idempotency_key="evt-123")

# delayed delivery (seconds)
client.publish(qid, {"ping": 1}, delay_seconds=30)

# scheduled for an absolute time
from datetime import datetime, timedelta, timezone
client.publish(qid, {"ping": 1}, deliver_at=datetime.now(timezone.utc) + timedelta(hours=1))`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Consumer — worker loop</CardTitle></CardHeader>
          <CardContent>
            <Code code={`from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("${base}", "fq_your_api_key")
consumer = FlowQueueConsumer(client, "<consumer_id>")

def handle(delivery):
    # return normally -> delivery completed
    # raise -> delivery failed (retry, then dead-letter per queue config)
    process(delivery.payload)

consumer.run(handle, poll_interval=2.0)`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Management, replay & DLQ</CardTitle></CardHeader>
          <CardContent>
            <Code code={`# queues
client.pause_queue(qid); client.resume_queue(qid)
client.update_queue(qid, max_retries=10)
client.queue_stats(qid)
client.queue_timeseries(qid, minutes=60)

# consumers
client.create_consumer(qid, "eu-hook", type="webhook",
                       endpoint_url="https://example.com/hook",
                       signing_secret="whsec_...",
                       routing_rules=[{"field":"payload.country","operator":"equals","value":"IN"}],
                       match_mode="any", auto_complete=False)
client.test_consumer(qid, consumer_id)

# replay
client.replay_failed(consumer_id)
client.replay_backfill(consumer_id)

# dead-letter queue
dead = client.dlq_list(qid)
client.requeue(delivery_id)      # one
client.requeue_all(qid)          # bulk
client.discard(delivery_id)`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>API keys & errors</CardTitle></CardHeader>
          <CardContent>
            <Code code={`# scoped key (token shown once)
key = client.create_api_key("ci-publisher", scopes=["publish"])
print(key["token"])

from flowqueue import ApiError
try:
    client.publish(qid, {"x": 1})
except ApiError as e:
    print(e.status, e.code, e.message)`} />
            <p className="mt-3 text-sm text-muted-foreground">
              Full HTTP API reference: <a href="/docs" className="text-primary hover:underline">/docs</a> (OpenAPI).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
