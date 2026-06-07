import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CodeBlock } from '@/components/marketing/CodeBlock';
import { DocsShell, DocSection } from './DocsShell';

const sections = [
  { id: 'auth', label: 'Authentication' },
  { id: 'setup', label: 'Create queue & consumer' },
  { id: 'publish', label: 'Publish a message' },
  { id: 'poll', label: 'Poll for work' },
  { id: 'ack', label: 'Complete / fail' },
  { id: 'loop', label: 'Full pull loop' },
];

const methodColor: Record<string, string> = {
  GET: 'bg-sky-500/15 text-sky-500',
  POST: 'bg-primary/15 text-primary',
};

function Endpoint({ method, path }: { method: 'GET' | 'POST'; path: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/60 px-3 py-2 font-mono text-sm">
      <span className={`rounded px-2 py-0.5 text-xs font-bold ${methodColor[method]}`}>
        {method}
      </span>
      <span className="break-all">{path}</span>
    </div>
  );
}

export function ApiDocs() {
  return (
    <DocsShell
      title="HTTP pull API"
      subtitle="Consume FlowQueue from any language over plain HTTP: publish messages, poll for deliveries, and acknowledge results. All routes are under /api/v1."
      sections={sections}
      action={
        <a href="/docs" target="_blank" rel="noreferrer">
          <Button variant="outline">
            OpenAPI / Swagger <ExternalLink size={14} />
          </Button>
        </a>
      }
    >
      <DocSection id="auth" title="Authentication">
        <p className="text-muted-foreground">
          Every request is authenticated with an API key in the <code>Authorization</code> header.
          Keys are scoped — publishing needs the <code>publish</code> scope, polling and
          acknowledging need <code>consume</code>. Create keys from the dashboard or the SDK; the
          token is shown once.
        </p>
        <CodeBlock lang="http" code={`Authorization: Bearer fq_your_api_key`} />
      </DocSection>

      <DocSection id="setup" title="Create a queue & an HTTP consumer">
        <Endpoint method="POST" path="/api/v1/queues" />
        <Endpoint method="POST" path="/api/v1/queues/{queue_id}/consumers" />
        <p className="text-muted-foreground">
          A queue holds messages; a consumer of type <code>http</code> pulls them. Each consumer
          gets its own independent delivery per message (fan-out).
        </p>
        <CodeBlock
          lang="bash"
          code={`# create a queue
curl -X POST https://api-flowqueue.skill.college/api/v1/queues \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "orders", "max_retries": 5, "dlq_enabled": true}'
# -> { "id": "<queue_id>", ... }

# create an http (pull) consumer on that queue
curl -X POST https://api-flowqueue.skill.college/api/v1/queues/<queue_id>/consumers \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "billing", "type": "http"}'
# -> { "id": "<consumer_id>", ... }`}
        />
      </DocSection>

      <DocSection id="publish" title="Publish a message">
        <Endpoint method="POST" path="/api/v1/queues/{queue_id}/messages" />
        <p className="text-muted-foreground">
          Provide a JSON <code>payload</code>. Optional <code>idempotency_key</code> dedupes
          retries; <code>delay_seconds</code> defers delivery. Needs the <code>publish</code> scope.
        </p>
        <CodeBlock
          lang="bash"
          code={`curl -X POST https://api-flowqueue.skill.college/api/v1/queues/<queue_id>/messages \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{
        "payload": {"order_id": 42, "total": 19.99},
        "idempotency_key": "order-42",
        "delay_seconds": 0
      }'`}
        />
      </DocSection>

      <DocSection id="poll" title="Poll for the next delivery">
        <Endpoint method="POST" path="/api/v1/consumers/{consumer_id}/poll" />
        <p className="text-muted-foreground">
          Returns the next available delivery and marks it <code>processing</code> under a
          visibility timeout. Returns <code>204 No Content</code> when the queue is empty. Needs the{' '}
          <code>consume</code> scope.
        </p>
        <CodeBlock
          lang="bash"
          code={`curl -X POST https://api-flowqueue.skill.college/api/v1/consumers/<consumer_id>/poll \\
  -H "Authorization: Bearer fq_your_api_key"

# 200 OK
# {
#   "id": "<delivery_id>",
#   "status": "processing",
#   "attempt": 1,
#   "payload": {"order_id": 42, "total": 19.99},
#   "sequence_num": 17
# }
#
# 204 No Content  -> nothing to do right now`}
        />
      </DocSection>

      <DocSection id="ack" title="Complete or fail a delivery">
        <Endpoint method="POST" path="/api/v1/deliveries/{delivery_id}/complete" />
        <Endpoint method="POST" path="/api/v1/deliveries/{delivery_id}/fail" />
        <p className="text-muted-foreground">
          After processing, acknowledge the outcome. <code>complete</code> marks success;{' '}
          <code>fail</code> schedules a retry, and after <code>max_retries</code> the delivery is
          dead-lettered. An optional <code>remark</code> is recorded in the audit log.
        </p>
        <CodeBlock
          lang="bash"
          code={`# success
curl -X POST https://api-flowqueue.skill.college/api/v1/deliveries/<delivery_id>/complete \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"remark": "charged ok"}'

# failure (will retry, then dead-letter)
curl -X POST https://api-flowqueue.skill.college/api/v1/deliveries/<delivery_id>/fail \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"remark": "payment gateway timeout"}'`}
        />
      </DocSection>

      <DocSection id="loop" title="A full pull loop">
        <p className="text-muted-foreground">
          The whole consume cycle in a shell loop — poll, process, acknowledge, repeat.
        </p>
        <CodeBlock
          lang="bash"
          code={`HOST=https://api-flowqueue.skill.college
KEY="Authorization: Bearer fq_your_api_key"
CID=<consumer_id>

while true; do
  resp=$(curl -s -w "\\n%{http_code}" -X POST "$HOST/api/v1/consumers/$CID/poll" -H "$KEY")
  body=$(echo "$resp" | head -n1); code=$(echo "$resp" | tail -n1)

  if [ "$code" = "204" ]; then sleep 2; continue; fi

  did=$(echo "$body" | jq -r .id)
  # ... process $body ...
  curl -s -X POST "$HOST/api/v1/deliveries/$did/complete" -H "$KEY" \\
    -H "Content-Type: application/json" -d '{"remark":"done"}' >/dev/null
done`}
        />
        <div className="mt-4 rounded-xl border border-border bg-card/60 p-4 text-sm text-muted-foreground">
          Prefer Python? The{' '}
          <a href="/docs/sdk" className="text-primary hover:underline">
            SDK
          </a>{' '}
          wraps this loop with automatic retries. Full schema:{' '}
          <a href="/docs" className="text-primary hover:underline">
            OpenAPI reference
          </a>
          .
        </div>
      </DocSection>
    </DocsShell>
  );
}
