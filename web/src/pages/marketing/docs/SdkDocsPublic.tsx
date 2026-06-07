import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/Reveal";
import { CodeBlock } from "@/components/marketing/CodeBlock";
import { DocsShell, DocSection } from "./DocsShell";

const sections = [
  { id: "install", label: "Install" },
  { id: "quickstart", label: "Quickstart" },
  { id: "producer", label: "Producer" },
  { id: "consumer", label: "Consumer loop" },
  { id: "manage", label: "Manage, replay & DLQ" },
  { id: "keys", label: "API keys & errors" },
];

export function SdkDocsPublic() {
  return (
    <DocsShell
      title="Python SDK"
      subtitle="The official flowqueue client — install, produce, consume and manage queues."
      sections={sections}
      action={
        <a href="https://pypi.org/project/flowqueue/" target="_blank" rel="noreferrer">
          <Button variant="outline">
            View on PyPI <ExternalLink size={14} />
          </Button>
        </a>
      }
    >
      <DocSection id="install" title="Install">
        <p className="text-muted-foreground">Requires Python 3.8+.</p>
        <CodeBlock lang="bash" code={`pip install flowqueue`} />
      </DocSection>

      <DocSection id="quickstart" title="Quickstart">
        <p className="text-muted-foreground">
          Create a queue and a pull consumer, publish a message, and consume one delivery.
        </p>
        <CodeBlock
          lang="python"
          code={`from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("https://your-host", "fq_your_api_key")

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
    c.complete(d.id, remark="done")`}
        />
      </DocSection>

      <DocSection id="producer" title="Producer — publish & schedule">
        <CodeBlock
          lang="python"
          code={`# immediate
client.publish(qid, {"hello": "world"})

# idempotent (dedup by key)
client.publish(qid, {"hello": "world"}, idempotency_key="evt-123")

# delayed delivery (seconds)
client.publish(qid, {"ping": 1}, delay_seconds=30)

# scheduled for an absolute time
from datetime import datetime, timedelta, timezone
client.publish(qid, {"ping": 1},
               deliver_at=datetime.now(timezone.utc) + timedelta(hours=1))`}
        />
      </DocSection>

      <DocSection id="consumer" title="Consumer — worker loop">
        <p className="text-muted-foreground">
          Return normally to complete a delivery; raise to fail it (it retries, then
          dead-letters per the queue config).
        </p>
        <CodeBlock
          lang="python"
          code={`from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("https://your-host", "fq_your_api_key")
consumer = FlowQueueConsumer(client, "<consumer_id>")

def handle(delivery):
    process(delivery.payload)

consumer.run(handle, poll_interval=2.0)`}
        />
      </DocSection>

      <DocSection id="manage" title="Management, replay & DLQ">
        <CodeBlock
          lang="python"
          code={`# queues
client.pause_queue(qid); client.resume_queue(qid)
client.update_queue(qid, max_retries=10)
client.queue_stats(qid)
client.queue_timeseries(qid, minutes=60)

# webhook consumer with conditional routing
client.create_consumer(qid, "eu-hook", type="webhook",
                       endpoint_url="https://example.com/hook",
                       signing_secret="whsec_...",
                       routing_rules=[{"field": "payload.country",
                                       "operator": "equals", "value": "IN"}],
                       match_mode="any", auto_complete=False)

# replay
client.replay_failed(consumer_id)
client.replay_backfill(consumer_id)

# dead-letter queue
dead = client.dlq_list(qid)
client.requeue(delivery_id)      # one
client.requeue_all(qid)          # bulk
client.discard(delivery_id)`}
        />
      </DocSection>

      <DocSection id="keys" title="API keys & errors">
        <CodeBlock
          lang="python"
          code={`# scoped key (token shown once)
key = client.create_api_key("ci-publisher", scopes=["publish"])
print(key["token"])

from flowqueue import ApiError
try:
    client.publish(qid, {"x": 1})
except ApiError as e:
    print(e.status, e.code, e.message)`}
        />
        <Reveal className="mt-4 rounded-xl border border-border bg-card/60 p-4 text-sm text-muted-foreground">
          Prefer raw HTTP? See the{" "}
          <a href="/docs/api" className="text-primary hover:underline">HTTP pull API docs</a> or
          the full <a href="/docs" className="text-primary hover:underline">OpenAPI reference</a>.
        </Reveal>
      </DocSection>
    </DocsShell>
  );
}
