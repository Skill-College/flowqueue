import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, ArrowRight, ChevronLeft, Trash2, Archive, RotateCcw, Pencil, Pause, Play, Copy, Check } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import type { Consumer, ConsumerType, Delivery, Message, Page, Queue, QueueLog, QueueStats, RoutingRule } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Tabs } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { JsonView } from "@/components/JsonView";
import { formatDate, buildCustomHeaders, copy } from "@/lib/utils";

const queueActionColors: Record<string, string> = {
  queue_created: "bg-primary",
  queue_updated: "bg-sky-400",
  queue_paused: "bg-amber-400",
  queue_resumed: "bg-emerald-400",
  queue_archived: "bg-amber-500",
  queue_restored: "bg-emerald-500",
  queue_purged: "bg-red-500",
  messages_expired: "bg-rose-400",
};

export function QueueDetail() {
  const { queueId = "" } = useParams();
  const qc = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [pubOpen, setPubOpen] = useState(false);
  const [consOpen, setConsOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [tlAction, setTlAction] = useState("");

  const queueQ = useQuery({
    queryKey: ["queue", queueId],
    queryFn: async () => (await api.get<Queue>(`/queues/${queueId}`)).data,
  });
  const statsQ = useQuery({
    queryKey: ["queue-stats", queueId],
    queryFn: async () => (await api.get<QueueStats>(`/queues/${queueId}/stats`)).data,
  });
  const messagesQ = useQuery({
    queryKey: ["messages", queueId],
    queryFn: async () =>
      (await api.get<Page<Message>>(`/queues/${queueId}/messages`, { params: { limit: 50 } })).data,
    enabled: tab === "messages",
  });
  const consumersQ = useQuery({
    queryKey: ["consumers", queueId],
    queryFn: async () =>
      (await api.get<Page<Consumer>>(`/queues/${queueId}/consumers`, { params: { limit: 50 } })).data,
    enabled: tab === "consumers" || tab === "overview",
  });

  const timelineQ = useQuery({
    queryKey: ["queue-timeline", queueId, tlAction],
    queryFn: async () =>
      (
        await api.get<Page<QueueLog>>(`/queues/${queueId}/timeline`, {
          params: { limit: 100, ...(tlAction ? { action: tlAction } : {}) },
        })
      ).data,
    enabled: tab === "timeline",
  });

  const queue = queueQ.data;
  const stats = statsQ.data;

  const archive = useMutation({
    mutationFn: async () => api.delete(`/queues/${queueId}`),
    onSuccess: () => {
      toast.success("Queue archived");
      qc.invalidateQueries({ queryKey: ["queue", queueId] });
      qc.invalidateQueries({ queryKey: ["queues"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const restore = useMutation({
    mutationFn: async () => api.patch(`/queues/${queueId}`, { is_active: true }),
    onSuccess: () => {
      toast.success("Queue restored");
      qc.invalidateQueries({ queryKey: ["queue", queueId] });
      qc.invalidateQueries({ queryKey: ["queues"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const pauseToggle = useMutation({
    mutationFn: async () =>
      api.post(`/queues/${queueId}/${queue?.is_paused ? "resume" : "pause"}`),
    onSuccess: () => {
      toast.success(queue?.is_paused ? "Queue resumed" : "Queue paused");
      qc.invalidateQueries({ queryKey: ["queue", queueId] });
      qc.invalidateQueries({ queryKey: ["queue-timeline", queueId] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const purge = useMutation({
    mutationFn: async () =>
      (await api.post<{ deliveries: number; messages: number }>(`/queues/${queueId}/purge`)).data,
    onSuccess: (data) => {
      toast.success(`Purged ${data.messages} pending messages`);
      setPurgeOpen(false);
      qc.invalidateQueries({ queryKey: ["queue-stats", queueId] });
      qc.invalidateQueries({ queryKey: ["messages", queueId] });
      qc.invalidateQueries({ queryKey: ["queue-timeline", queueId] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <div>
      <Link to="/queues" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ChevronLeft size={16} /> Queues
      </Link>
      <PageHeader
        title={queue?.name ?? "Queue"}
        description={queue ? `${queue.fifo_enabled ? "FIFO" : "Standard"} · max ${queue.max_retries} retries · visibility ${queue.visibility_timeout_seconds}s` : ""}
        action={
          <div className="flex flex-wrap gap-2">
            {queue && !queue.is_active ? (
              <Button variant="default" onClick={() => restore.mutate()} disabled={restore.isPending}>
                <RotateCcw size={16} /> Restore
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setConsOpen(true)}>
                  <Plus size={16} /> Consumer
                </Button>
                <Button variant="outline" onClick={() => setPubOpen(true)}>
                  <Send size={16} /> Publish
                </Button>
                <Button variant="ghost" onClick={() => setEditOpen(true)}>
                  <Pencil size={16} /> Edit
                </Button>
                {queue?.is_paused ? (
                  <Button variant="ghost" onClick={() => pauseToggle.mutate()} disabled={pauseToggle.isPending}>
                    <Play size={16} className="text-emerald-500" /> Resume
                  </Button>
                ) : (
                  <ConfirmButton
                    variant="ghost"
                    title="Pause queue"
                    description="Pausing stops delivery (poll + webhook dispatch). Publishing still works; messages queue up until you resume."
                    confirmLabel="Pause"
                    disabled={pauseToggle.isPending}
                    onConfirm={() => pauseToggle.mutate()}
                  >
                    <Pause size={16} className="text-amber-500" /> Pause
                  </ConfirmButton>
                )}
                <Button variant="ghost" onClick={() => setPurgeOpen(true)}>
                  <Trash2 size={16} className="text-red-500" /> Purge
                </Button>
                <ConfirmButton
                  variant="ghost"
                  title="Archive queue"
                  description={`Archiving "${queue?.name ?? ""}" blocks publishing until restored. Existing messages are kept.`}
                  confirmLabel="Archive"
                  disabled={archive.isPending}
                  onConfirm={() => archive.mutate()}
                >
                  <Archive size={16} className="text-amber-500" /> Archive
                </ConfirmButton>
              </>
            )}
          </div>
        }
      />

      {queue && !queue.is_active && (
        <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-600 dark:text-amber-400">
          This queue is archived. Publishing is blocked until you restore it.
        </div>
      )}
      {queue && queue.is_active && queue.is_paused && (
        <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-600 dark:text-amber-400">
          This queue is paused. Messages still publish, but delivery (poll + webhook) is stopped.
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Pending" value={stats?.pending} tint="text-amber-400" />
        <Stat label="Processing" value={stats?.processing} tint="text-sky-400" />
        <Stat label="Completed" value={stats?.completed} tint="text-emerald-400" />
        <Stat label="Failed" value={stats?.failed} tint="text-red-400" />
      </div>

      <Tabs
        className="mb-4"
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "consumers", label: "Consumers" },
          { id: "messages", label: "Messages" },
          { id: "dlq", label: "Dead Letter" },
          { id: "timeline", label: "Timeline" },
        ]}
      />

      {tab === "overview" && <TimeseriesCard queueId={queueId} />}
      {tab === "overview" && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Configuration</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row k="Total messages" v={stats?.total_messages} />
              <Row k="Consumers" v={stats?.consumer_count} />
              <Row k="Pending retention" v={queue ? `${queue.retention_seconds}s` : "—"} />
              <Row k="Success retention" v={queue ? `${queue.success_retention_seconds}s` : "—"} />
              <Row k="Failed retention" v={queue ? `${queue.failed_retention_seconds}s` : "—"} />
              <Row k="Retry delay" v={queue ? `${queue.retry_delay_seconds}s` : "—"} />
              <Row k="Max consumer lag" v={stats?.max_consumer_lag_seconds != null ? `${Math.round(stats.max_consumer_lag_seconds)}s` : "—"} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Consumers</CardTitle></CardHeader>
            <CardContent>
              <ConsumerList consumers={consumersQ.data?.items ?? []} />
            </CardContent>
          </Card>
        </div>
      )}
      {tab === "overview" && <PublishSnippet queueId={queueId} />}

      {tab === "consumers" && (
        <Card>
          <CardContent className="pt-6">
            <ConsumerList consumers={consumersQ.data?.items ?? []} />
          </CardContent>
        </Card>
      )}

      {tab === "messages" && (
        <Card>
          <CardContent className="pt-6">
            {messagesQ.data && messagesQ.data.items.length > 0 ? (
              <Table>
                <THead>
                  <TR>
                    <TH>Seq</TH>
                    <TH>Payload</TH>
                    <TH>Idempotency</TH>
                    <TH>Published</TH>
                  </TR>
                </THead>
                <TBody>
                  {messagesQ.data.items.map((m) => (
                    <TR key={m.id}>
                      <TD className="font-mono">{m.sequence_num}</TD>
                      <TD className="max-w-md truncate font-mono text-xs text-muted-foreground">
                        {JSON.stringify(m.payload)}
                      </TD>
                      <TD className="text-muted-foreground">{m.idempotency_key ?? "—"}</TD>
                      <TD className="text-muted-foreground">{formatDate(m.published_at)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-muted-foreground">No messages yet.</p>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "dlq" && <DlqTab queueId={queueId} />}

      {tab === "timeline" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle>Activity timeline</CardTitle>
            <Select className="w-52" value={tlAction} onChange={(e) => setTlAction(e.target.value)}>
              <option value="">All actions</option>
              <option value="queue_created">Created</option>
              <option value="queue_updated">Updated</option>
              <option value="queue_paused">Paused</option>
              <option value="queue_resumed">Resumed</option>
              <option value="queue_archived">Archived</option>
              <option value="queue_restored">Restored</option>
              <option value="queue_purged">Purged</option>
              <option value="messages_expired">Messages expired</option>
            </Select>
          </CardHeader>
          <CardContent>
            <ol className="relative space-y-5 border-l border-border pl-5">
              {(timelineQ.data?.items ?? []).map((log) => (
                <li key={log.id} className="relative">
                  <span
                    className={`absolute -left-[1.42rem] top-1 h-2.5 w-2.5 rounded-full ${
                      queueActionColors[log.action] ?? "bg-muted-foreground"
                    }`}
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium capitalize">
                      {log.action.replace(/^queue_/, "").replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-muted-foreground">{formatDate(log.created_at)}</span>
                  </div>
                  {log.remark && <p className="mt-1 text-sm text-muted-foreground">{log.remark}</p>}
                  {Object.keys(log.context ?? {}).length > 0 && (
                    <JsonView data={log.context} className="mt-2 max-h-40" />
                  )}
                </li>
              ))}
              {timelineQ.data?.items.length === 0 && (
                <li className="text-sm text-muted-foreground">No activity.</li>
              )}
            </ol>
          </CardContent>
        </Card>
      )}

      <Dialog open={purgeOpen} onClose={() => setPurgeOpen(false)} title="Purge queue">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Permanently delete all <span className="font-medium text-foreground">pending</span>{" "}
            messages in this queue ({stats?.pending ?? 0} pending). In-flight, completed, failed
            and dead-letter messages are kept. This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setPurgeOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => purge.mutate()}
              disabled={purge.isPending}
            >
              {purge.isPending ? "Purging…" : "Purge pending"}
            </Button>
          </div>
        </div>
      </Dialog>

      <PublishDialog open={pubOpen} onClose={() => setPubOpen(false)} queueId={queueId} onDone={() => {
        qc.invalidateQueries({ queryKey: ["messages", queueId] });
        qc.invalidateQueries({ queryKey: ["queue-stats", queueId] });
      }} />
      <ConsumerDialog open={consOpen} onClose={() => setConsOpen(false)} queueId={queueId} onDone={() => {
        qc.invalidateQueries({ queryKey: ["consumers", queueId] });
      }} />
      {queue && (
        <EditQueueDialog
          key={queue.updated_at ?? queue.created_at}
          open={editOpen}
          onClose={() => setEditOpen(false)}
          queue={queue}
          onDone={() => qc.invalidateQueries({ queryKey: ["queue", queueId] })}
        />
      )}
    </div>
  );
}

function CodeBlock({ code }: { code: string }) {
  const [done, setDone] = useState(false);
  return (
    <div className="relative">
      <pre className="max-h-80 overflow-auto rounded-lg border border-border bg-background/60 p-3 pr-10 text-xs leading-relaxed">
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

function PublishSnippet({ queueId }: { queueId: string }) {
  const base = window.location.origin;
  const [lang, setLang] = useState<"curl" | "python">("curl");
  const curl = `curl -X POST "${base}/api/v1/queues/${queueId}/messages" \\
  -H "Authorization: Bearer fq_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"payload": {"order_id": 42}, "idempotency_key": "order-42"}'`;
  const python = `import asyncio
from flowqueue import AsyncFlowQueueClient

async def main():
    async with AsyncFlowQueueClient("${base}", "fq_your_api_key") as client:
        await client.publish("${queueId}", {"order_id": 42}, idempotency_key="order-42")

asyncio.run(main())`;
  return (
    <Card className="mt-6">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>Publish a message</CardTitle>
        <div className="flex gap-1">
          <Button size="sm" variant={lang === "curl" ? "default" : "outline"} onClick={() => setLang("curl")}>
            curl
          </Button>
          <Button size="sm" variant={lang === "python" ? "default" : "outline"} onClick={() => setLang("python")}>
            Python
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <CodeBlock code={lang === "curl" ? curl : python} />
        <p className="mt-3 text-xs text-muted-foreground">
          Create an API key under <Link to="/api-keys" className="text-primary hover:underline">API Keys</Link>.
          Prefer a UI? Use the <span className="font-medium text-foreground">Publish</span> button above.
        </p>
      </CardContent>
    </Card>
  );
}

function TimeseriesCard({ queueId }: { queueId: string }) {
  const { data } = useQuery({
    queryKey: ["timeseries", queueId],
    queryFn: async () =>
      (await api.get<{ bucket: string; created: number; completed: number; failed: number }[]>(
        `/queues/${queueId}/timeseries`,
        { params: { minutes: 60 } }
      )).data,
  });
  const rows = (data ?? []).map((d) => ({
    t: new Date(d.bucket).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
    created: d.created,
    completed: d.completed,
    failed: d.failed,
  }));
  return (
    <Card>
      <CardHeader><CardTitle>Activity (last 60 min)</CardTitle></CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            No activity in the last hour.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="t" stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
              <Line type="monotone" dataKey="created" stroke="#1CB0F6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="completed" stroke="#58CC02" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="failed" stroke="#FF4B4B" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function DlqTab({ queueId }: { queueId: string }) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["dlq", queueId],
    queryFn: async () =>
      (await api.get<Page<Delivery>>(`/queues/${queueId}/dlq`, { params: { limit: 100 } })).data,
  });
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["dlq", queueId] });
    qc.invalidateQueries({ queryKey: ["queue-stats", queueId] });
  };
  const requeue = useMutation({
    mutationFn: async (id: string) => api.post(`/deliveries/${id}/requeue`),
    onSuccess: () => { toast.success("Requeued"); invalidate(); },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const discard = useMutation({
    mutationFn: async (id: string) => api.post(`/deliveries/${id}/discard`),
    onSuccess: () => { toast.success("Discarded"); invalidate(); },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const requeueAll = useMutation({
    mutationFn: async () => api.post(`/queues/${queueId}/dlq/requeue`),
    onSuccess: (r) => { toast.success(`Requeued ${r.data.requeued}`); invalidate(); },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-3 flex items-center justify-between">
          <Badge>{data?.total ?? 0} dead</Badge>
          {(data?.total ?? 0) > 0 && (
            <ConfirmButton
              size="sm"
              variant="outline"
              title="Requeue all dead letters"
              description={`Re-enqueues all ${data?.total ?? 0} dead-lettered deliveries for another attempt.`}
              confirmLabel="Requeue all"
              onConfirm={() => requeueAll.mutate()}
            >
              <RotateCcw size={14} /> Requeue all
            </ConfirmButton>
          )}
        </div>
        {data && data.items.length > 0 ? (
          <Table>
            <THead>
              <TR><TH>Delivery</TH><TH>Attempts</TH><TH>Remark</TH><TH></TH></TR>
            </THead>
            <TBody>
              {data.items.map((d) => (
                <TR key={d.id}>
                  <TD className="font-mono text-xs">{d.id.slice(0, 8)}</TD>
                  <TD>{d.attempt_count}</TD>
                  <TD className="max-w-xs truncate text-muted-foreground">{d.last_remark ?? "—"}</TD>
                  <TD>
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" onClick={() => requeue.mutate(d.id)}>
                        <RotateCcw size={14} /> Requeue
                      </Button>
                      <ConfirmButton
                        size="sm"
                        variant="ghost"
                        destructive
                        title="Discard delivery"
                        description="Permanently drops this dead-lettered delivery. It will not be retried."
                        confirmLabel="Discard"
                        onConfirm={() => discard.mutate(d.id)}
                      >
                        <Trash2 size={14} className="text-red-400" /> Discard
                      </ConfirmButton>
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <p className="py-8 text-center text-muted-foreground">Dead letter queue is empty.</p>
        )}
      </CardContent>
    </Card>
  );
}

function EditQueueDialog({
  open,
  onClose,
  queue,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  queue: Queue;
  onDone: () => void;
}) {
  const [maxRetries, setMaxRetries] = useState(queue.max_retries);
  const [retryDelay, setRetryDelay] = useState(queue.retry_delay_seconds);
  const [visibility, setVisibility] = useState(queue.visibility_timeout_seconds);
  const [retention, setRetention] = useState(queue.retention_seconds);
  const [successRetention, setSuccessRetention] = useState(queue.success_retention_seconds);
  const [failedRetention, setFailedRetention] = useState(queue.failed_retention_seconds);
  const [fifo, setFifo] = useState(queue.fifo_enabled);
  const [dlq, setDlq] = useState(queue.dlq_enabled);
  const [metadataText, setMetadataText] = useState(
    Object.keys(queue.metadata ?? {}).length ? JSON.stringify(queue.metadata, null, 2) : ""
  );

  const save = useMutation({
    mutationFn: async () => {
      let metadata: Record<string, unknown> | undefined;
      if (metadataText.trim()) {
        try {
          metadata = JSON.parse(metadataText);
        } catch {
          throw new Error("Metadata is not valid JSON");
        }
      }
      return api.patch(`/queues/${queue.id}`, {
        max_retries: maxRetries,
        retry_delay_seconds: retryDelay,
        visibility_timeout_seconds: visibility,
        retention_seconds: retention,
        success_retention_seconds: successRetention,
        failed_retention_seconds: failedRetention,
        fifo_enabled: fifo,
        dlq_enabled: dlq,
        ...(metadata !== undefined ? { metadata } : {}),
      });
    },
    onSuccess: () => { toast.success("Queue updated"); onDone(); onClose(); },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <Dialog open={open} onClose={onClose} title="Edit queue">
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5"><Label>Max retries</Label>
            <Input type="number" min={0} value={maxRetries} onChange={(e) => setMaxRetries(Number(e.target.value))} /></div>
          <div className="space-y-1.5"><Label>Retry delay (s)</Label>
            <Input type="number" min={0} value={retryDelay} onChange={(e) => setRetryDelay(Number(e.target.value))} /></div>
          <div className="space-y-1.5"><Label>Visibility timeout (s)</Label>
            <Input type="number" min={1} value={visibility} onChange={(e) => setVisibility(Number(e.target.value))} /></div>
          <div className="space-y-1.5"><Label>Pending retention (s)</Label>
            <Input type="number" min={1} value={retention} onChange={(e) => setRetention(Number(e.target.value))} /></div>
          <div className="space-y-1.5"><Label>Success retention (s)</Label>
            <Input type="number" min={1} value={successRetention} onChange={(e) => setSuccessRetention(Number(e.target.value))} /></div>
          <div className="space-y-1.5"><Label>Failed retention (s)</Label>
            <Input type="number" min={1} value={failedRetention} onChange={(e) => setFailedRetention(Number(e.target.value))} /></div>
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={fifo} onChange={(e) => setFifo(e.target.checked)} /> FIFO
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={dlq} onChange={(e) => setDlq(e.target.checked)} /> Dead-letter enabled
          </label>
        </div>
        <div className="space-y-1.5">
          <Label>Metadata (JSON)</Label>
          <Textarea value={metadataText} onChange={(e) => setMetadataText(e.target.value)} rows={3} placeholder='{"team":"payments"}' />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
        </div>
      </form>
    </Dialog>
  );
}

function Stat({ label, value, tint }: { label: string; value?: number; tint: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className={`text-2xl font-semibold ${tint}`}>{value ?? 0}</div>
        <div className="text-sm text-muted-foreground">{label}</div>
      </CardContent>
    </Card>
  );
}

function Row({ k, v }: { k: string; v?: string | number }) {
  return (
    <div className="flex justify-between border-b border-border/50 py-1.5 last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-medium">{v ?? "—"}</span>
    </div>
  );
}

function ConsumerList({ consumers }: { consumers: Consumer[] }) {
  if (consumers.length === 0)
    return <p className="py-6 text-center text-sm text-muted-foreground">No consumers yet.</p>;
  return (
    <div className="space-y-2">
      {consumers.map((c) => (
        <Link
          key={c.id}
          to={`/consumers/${c.id}`}
          className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 hover:bg-accent"
        >
          <div className="flex items-center gap-3">
            <Badge>{c.type}</Badge>
            <span className="font-medium">{c.name}</span>
            {!c.is_active && <span className="text-xs text-muted-foreground">inactive</span>}
          </div>
          <ArrowRight size={16} className="text-muted-foreground" />
        </Link>
      ))}
    </div>
  );
}

function PublishDialog({
  open,
  onClose,
  queueId,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  queueId: string;
  onDone: () => void;
}) {
  const [payload, setPayload] = useState('{\n  "hello": "world"\n}');
  const [idem, setIdem] = useState("");
  const [delay, setDelay] = useState(0);

  const pub = useMutation({
    mutationFn: async () => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(payload);
      } catch {
        throw new Error("Payload is not valid JSON");
      }
      return (
        await api.post(`/queues/${queueId}/messages`, {
          payload: parsed,
          idempotency_key: idem || null,
          delay_seconds: delay > 0 ? delay : null,
        })
      ).data;
    },
    onSuccess: () => {
      toast.success("Message published");
      onDone();
      onClose();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <Dialog open={open} onClose={onClose} title="Publish message">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>Payload (JSON)</Label>
          <Textarea value={payload} onChange={(e) => setPayload(e.target.value)} rows={6} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Idempotency key (optional)</Label>
            <Input value={idem} onChange={(e) => setIdem(e.target.value)} placeholder="order-42" />
          </div>
          <div className="space-y-1.5">
            <Label>Delay (seconds)</Label>
            <Input type="number" min={0} value={delay} onChange={(e) => setDelay(Number(e.target.value))} />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => pub.mutate()} disabled={pub.isPending}>
            {pub.isPending ? "Publishing…" : "Publish"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function ConsumerDialog({
  open,
  onClose,
  queueId,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  queueId: string;
  onDone: () => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState<ConsumerType>("http");
  const [endpoint, setEndpoint] = useState("");
  const [autoComplete, setAutoComplete] = useState(true);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [matchMode, setMatchMode] = useState<"any" | "all">("any");
  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
  const isPush = type === "webhook";

  const reset = () => {
    setName("");
    setEndpoint("");
    setAutoComplete(true);
    setRules([]);
    setMatchMode("any");
    setHeaders([]);
    setType("http");
  };

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/queues/${queueId}/consumers`, {
          name,
          type,
          endpoint_url: isPush ? endpoint : null,
          auto_complete: isPush ? autoComplete : true,
          match_mode: matchMode,
          custom_headers: isPush ? buildCustomHeaders(headers) : {},
          routing_rules: isPush
            ? rules
                .filter((r) => r.field)
                .map((r) => {
                  const n = Number(r.value);
                  const value =
                    r.value !== "" && !Number.isNaN(n) ? n : r.value;
                  return { ...r, value };
                })
            : [],
        })
      ).data,
    onSuccess: () => {
      toast.success("Consumer created");
      onDone();
      onClose();
      reset();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const addRule = () =>
    setRules((r) => [...r, { field: "payload.", operator: "equals", value: "" }]);
  const updateRule = (i: number, patch: Partial<RoutingRule>) =>
    setRules((r) => r.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
  const removeRule = (i: number) => setRules((r) => r.filter((_, idx) => idx !== i));

  const addHeader = () => setHeaders((h) => [...h, { key: "", value: "" }]);
  const updateHeader = (i: number, patch: Partial<{ key: string; value: string }>) =>
    setHeaders((h) => h.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
  const removeHeader = (i: number) => setHeaders((h) => h.filter((_, idx) => idx !== i));

  return (
    <Dialog open={open} onClose={onClose} title="New consumer" className="max-w-2xl">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select value={type} onChange={(e) => setType(e.target.value as ConsumerType)}>
              <option value="http">http (pull)</option>
              <option value="sdk">sdk (pull)</option>
              <option value="webhook">webhook (push)</option>
            </Select>
          </div>
        </div>

        {isPush && (
          <>
            <div className="space-y-1.5">
              <Label>Endpoint URL</Label>
              <Input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="https://example.com/hook"
                required
              />
              <p className="text-xs text-muted-foreground">Private/loopback IPs are blocked (SSRF).</p>
            </div>

            <label className="flex items-start gap-2 rounded-lg border border-border p-3 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={autoComplete}
                onChange={(e) => setAutoComplete(e.target.checked)}
              />
              <span>
                <span className="font-medium">Auto-complete on 2xx</span>
                <span className="block text-xs text-muted-foreground">
                  On: mark delivery completed when your endpoint returns 2xx. Off: stays
                  “processing” until your receiver calls back complete/fail (visibility
                  timeout redelivers if no callback).
                </span>
              </span>
            </label>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Custom headers (optional)</Label>
                <Button type="button" variant="ghost" size="sm" onClick={addHeader}>
                  <Plus size={14} /> Add header
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Sent on every POST so your receiver can validate the call (e.g.
                Authorization). Reserved X-FlowQueue-* and the signature header can’t be
                overridden.
              </p>
              {headers.map((h, i) => (
                <div key={i} className="grid grid-cols-12 items-center gap-2">
                  <Input
                    className="col-span-5"
                    placeholder="X-Api-Key"
                    value={h.key}
                    onChange={(e) => updateHeader(i, { key: e.target.value })}
                  />
                  <Input
                    className="col-span-6"
                    placeholder="value"
                    value={h.value}
                    onChange={(e) => updateHeader(i, { value: e.target.value })}
                  />
                  <Button type="button" variant="ghost" size="icon" className="col-span-1" onClick={() => removeHeader(i)}>
                    <Trash2 size={14} className="text-red-400" />
                  </Button>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Delivery filter rules (optional)</Label>
                <Button type="button" variant="ghost" size="sm" onClick={addRule}>
                  <Plus size={14} /> Add rule
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Rules gate delivery to the endpoint above by payload. No match → skipped
                (delivery marked completed). No rules → always deliver.
              </p>
              {rules.length > 0 && (
                <div className="flex items-center gap-2">
                  <Label>Match</Label>
                  <Select
                    className="w-44"
                    value={matchMode}
                    onChange={(e) => setMatchMode(e.target.value as "any" | "all")}
                  >
                    <option value="any">any rule (OR)</option>
                    <option value="all">all rules (AND)</option>
                  </Select>
                </div>
              )}
              {rules.map((r, i) => (
                <div key={i} className="grid grid-cols-12 items-center gap-2">
                  <Input
                    className="col-span-5"
                    placeholder="payload.country"
                    value={r.field}
                    onChange={(e) => updateRule(i, { field: e.target.value })}
                  />
                  <Select
                    className="col-span-3"
                    value={r.operator}
                    onChange={(e) => updateRule(i, { operator: e.target.value })}
                  >
                    <option value="equals">equals</option>
                    <option value="not_equals">not_equals</option>
                    <option value="contains">contains</option>
                    <option value="greater_than">greater_than</option>
                    <option value="less_than">less_than</option>
                  </Select>
                  <Input
                    className="col-span-3"
                    placeholder="value"
                    value={String(r.value ?? "")}
                    onChange={(e) => updateRule(i, { value: e.target.value })}
                  />
                  <Button type="button" variant="ghost" size="icon" className="col-span-1" onClick={() => removeRule(i)}>
                    <Trash2 size={14} className="text-red-400" />
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
