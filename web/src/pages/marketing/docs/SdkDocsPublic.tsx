import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Reveal } from '@/components/marketing/Reveal';
import { CodeBlock } from '@/components/marketing/CodeBlock';
import { DocsShell, DocSection } from './DocsShell';

const sections = [
  { id: 'install', label: 'Install' },
  { id: 'quickstart', label: 'Quickstart' },
  { id: 'producer', label: 'Producer' },
  { id: 'consumer', label: 'Consumer loop' },
  { id: 'errors', label: 'Errors' },
];

export function SdkDocsPublic() {
  return (
    <DocsShell
      title="Python SDK"
      subtitle="The official flowqueue client — async, typed; publish and consume."
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
        <p className="text-muted-foreground">
          Async, typed runtime client (publish + consume). Requires Python 3.9+. Manage
          queues, consumers and API keys in the dashboard.
        </p>
        <CodeBlock lang="bash" code={`pip install flowqueue`} />
      </DocSection>

      <DocSection id="quickstart" title="Quickstart">
        <p className="text-muted-foreground">
          Create the queue and consumer in the dashboard, then publish and consume by id.
        </p>
        <CodeBlock
          lang="python"
          code={`import asyncio
from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

async def main():
    async with AsyncFlowQueueClient("https://api-flowqueue.skill.college", "fq_key") as client:
        # Publish
        await client.publish("<queue_id>", {"order_id": 42}, idempotency_key="order-42")

        # Consume one delivery
        c = AsyncFlowQueueConsumer(client, "<consumer_id>")
        d = await c.poll()
        if d:
            print(d["payload"])
            await c.complete(d["id"], remark="done")

asyncio.run(main())`}
        />
      </DocSection>

      <DocSection id="producer" title="Producer — publish & schedule">
        <CodeBlock
          lang="python"
          code={`# immediate
await client.publish(qid, {"hello": "world"})

# idempotent (dedup by key)
await client.publish(qid, {"hello": "world"}, idempotency_key="evt-123")

# delayed delivery (seconds)
await client.publish(qid, {"ping": 1}, delay_seconds=30)

# scheduled for an absolute time
from datetime import datetime, timedelta, timezone
await client.publish(qid, {"ping": 1},
                     deliver_at=datetime.now(timezone.utc) + timedelta(hours=1))`}
        />
      </DocSection>

      <DocSection id="consumer" title="Consumer — worker loop">
        <p className="text-muted-foreground">
          The handler may be sync or async. Return normally to complete a delivery; raise to
          fail it (it retries, then dead-letters per the queue config).
        </p>
        <CodeBlock
          lang="python"
          code={`import asyncio
from flowqueue import AsyncFlowQueueClient, AsyncFlowQueueConsumer

async def handle(delivery):
    await process(delivery["payload"])

async def main():
    async with AsyncFlowQueueClient("https://api-flowqueue.skill.college", "fq_key") as client:
        consumer = AsyncFlowQueueConsumer(client, "<consumer_id>")
        await consumer.run(handle, poll_interval=2.0)

asyncio.run(main())`}
        />
      </DocSection>

      <DocSection id="errors" title="Errors">
        <CodeBlock
          lang="python"
          code={`from flowqueue import ApiError

try:
    await client.publish(qid, {"x": 1})
except ApiError as e:
    print(e.status, e.code, e.message)`}
        />
        <Reveal className="mt-4 rounded-xl border border-border bg-card/60 p-4 text-sm text-muted-foreground">
          Queue/consumer management, replay & DLQ live in the dashboard. Prefer raw HTTP? See the{' '}
          <a href="/docs/api" className="text-primary hover:underline">
            HTTP pull API docs
          </a>{' '}
          or the full{' '}
          <a href="/docs" className="text-primary hover:underline">
            OpenAPI reference
          </a>
          .
        </Reveal>
      </DocSection>
    </DocsShell>
  );
}
