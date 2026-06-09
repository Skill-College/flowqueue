import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Download, RefreshCw, History, Copy, Check, Power, Pencil, Send, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import type { Consumer, Delivery, DeliveryStatus, Page, RoutingRule } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog } from "@/components/ui/dialog";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { Pagination } from "@/components/ui/pagination";
import { formatDate, shortId, copy } from "@/lib/utils";

const STATUSES: (DeliveryStatus | "")[] = ["", "pending", "processing", "completed", "failed"];

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      size="icon"
      variant="ghost"
      className="h-7 w-7"
      onClick={async () => {
        await copy(text);
        setDone(true);
        toast.success("Copied");
        setTimeout(() => setDone(false), 1200);
      }}
    >
      {done ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
    </Button>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="relative">
      <pre className="max-h-96 overflow-auto rounded-lg border border-border bg-background/60 p-3 pr-10 text-xs leading-relaxed">
        <code>{code}</code>
      </pre>
      <div className="absolute right-2 top-2">
        <CopyButton text={code} />
      </div>
    </div>
  );
}

function Usage({ consumer }: { consumer: Consumer }) {
  const base = window.location.origin;
  const cid = consumer.id;

  if (consumer.type === "http") {
    const code = `# 1. Mint an API key in the API Keys page, then:
export TOKEN=fq_xxx
export BASE=${base}

# 2. Poll the next delivery (claims it -> processing)
curl -s -X POST $BASE/api/v1/consumers/${cid}/poll \\
  -H "Authorization: Bearer $TOKEN"
# -> { "id": "<delivery_id>", "payload": {...}, "sequence_num": 1, ... }

# 3. Acknowledge success
curl -s -X POST $BASE/api/v1/deliveries/<delivery_id>/complete \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"remark":"processed"}'

# or report failure (auto-retries until max_retries)
curl -s -X POST $BASE/api/v1/deliveries/<delivery_id>/fail \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"remark":"boom","metadata":{}}'`;
    return <CodeBlock code={code} />;
  }

  if (consumer.type === "sdk") {
    const code = `pip install flowqueue

from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("${base}", "fq_xxx")   # your API key
consumer = FlowQueueConsumer(client, "${cid}")

d = consumer.poll()                 # claim next delivery (or None)
if d:
    try:
        handle(d.payload)           # your work here
        consumer.complete(d.id, remark="ok")
    except Exception as e:
        consumer.fail(d.id, remark=str(e))`;
    return <CodeBlock code={code} />;
  }

  // webhook
  const headers = `POST ${consumer.endpoint_url ?? "<endpoint_url>"}
Content-Type: application/json
X-FlowQueue-Delivery-ID: <delivery_id>
X-FlowQueue-Message-ID: <message_id>
X-FlowQueue-Timestamp: <iso8601>

<your message payload>`;
  const callback = `# Your receiver must acknowledge using the delivery id from the header:
export TOKEN=fq_xxx
export BASE=${base}

curl -s -X POST $BASE/api/v1/deliveries/<X-FlowQueue-Delivery-ID>/complete \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"remark":"done"}'
# or /fail to trigger a retry`;
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-1 text-sm font-medium">FlowQueue sends this request to your endpoint:</p>
        <CodeBlock code={headers} />
      </div>
      {consumer.auto_complete ? (
        <p className="text-sm text-muted-foreground">
          Auto-complete is <span className="text-emerald-400">on</span>: returning HTTP 2xx
          marks the delivery completed. Non-2xx retries up to the queue's max retries.
        </p>
      ) : (
        <div>
          <p className="mb-1 text-sm">
            Auto-complete is <span className="text-amber-400">off</span>: after you return 2xx
            the delivery stays <span className="font-medium">processing</span> until you call
            back. No callback before the visibility timeout → it is redelivered, then failed.
          </p>
          <CodeBlock code={callback} />
        </div>
      )}
    </div>
  );
}

export function ConsumerDetail() {
  const { consumerId = "" } = useParams();
  const qc = useQueryClient();
  const [status, setStatus] = useState<DeliveryStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const LIMIT = 20;

  const consumerQ = useQuery({
    queryKey: ["consumer", consumerId],
    queryFn: async () => (await api.get<Consumer>(`/consumers/${consumerId}`)).data,
  });
  const deliveriesQ = useQuery({
    queryKey: ["deliveries", consumerId, status, offset],
    queryFn: async () =>
      (
        await api.get<Page<Delivery>>(`/consumers/${consumerId}/deliveries`, {
          params: { limit: LIMIT, offset, ...(status ? { status } : {}) },
        })
      ).data,
  });

  const consumer = consumerQ.data;
  const isPull = consumer?.type === "http" || consumer?.type === "sdk";

  const refetchAll = () => qc.invalidateQueries({ queryKey: ["deliveries", consumerId] });
  const refetchConsumer = () => qc.invalidateQueries({ queryKey: ["consumer", consumerId] });

  const toggleActive = useMutation({
    mutationFn: async () => {
      if (!consumer) return;
      return (
        await api.patch(`/queues/${consumer.queue_id}/consumers/${consumer.id}`, {
          is_active: !consumer.is_active,
        })
      ).data;
    },
    onSuccess: () => {
      toast.success(consumer?.is_active ? "Consumer disabled" : "Consumer enabled");
      refetchConsumer();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const poll = useMutation({
    mutationFn: async () => (await api.post(`/consumers/${consumerId}/poll`)).data,
    onSuccess: (data) => {
      if (!data) toast.info("No pending deliveries");
      else toast.success(`Claimed delivery ${shortId(data.id)} (seq ${data.sequence_num})`);
      refetchAll();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const replayFailed = useMutation({
    mutationFn: async () => (await api.post(`/consumers/${consumerId}/replay/failed`)).data,
    onSuccess: () => {
      toast.success("Replay (failed) queued");
      refetchAll();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const backfill = useMutation({
    mutationFn: async () => (await api.post(`/consumers/${consumerId}/replay/backfill`)).data,
    onSuccess: () => {
      toast.success("Backfill queued");
      refetchAll();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });
  const sendTest = useMutation({
    mutationFn: async () =>
      (await api.post(`/queues/${consumer?.queue_id}/consumers/${consumerId}/test`)).data,
    onSuccess: (r) =>
      r.success
        ? toast.success(`Test delivered (HTTP ${r.status_code})`)
        : toast.error(`Test failed: ${r.detail ?? r.status_code}`),
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <div>
      {consumer && (
        <Link
          to={`/queues/${consumer.queue_id}`}
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft size={16} /> Back to queue
        </Link>
      )}
      <PageHeader
        title={consumer?.name ?? "Consumer"}
        description={consumer ? consumer.type + (consumer.endpoint_url ? " · " + consumer.endpoint_url : "") : ""}
        action={
          <div className="flex flex-wrap gap-2">
            {consumer && (
              <Button variant="ghost" onClick={() => setEditOpen(true)}>
                <Pencil size={16} /> Edit
              </Button>
            )}
            {consumer?.type === "webhook" && (
              <Button variant="outline" onClick={() => sendTest.mutate()} disabled={sendTest.isPending}>
                <Send size={16} /> Send test
              </Button>
            )}
            {consumer && (
              <Button
                variant={consumer.is_active ? "outline" : "default"}
                onClick={() => toggleActive.mutate()}
                disabled={toggleActive.isPending}
              >
                <Power size={16} /> {consumer.is_active ? "Disable" : "Enable"}
              </Button>
            )}
            {isPull && (
              <Button variant="outline" onClick={() => poll.mutate()} disabled={poll.isPending}>
                <Download size={16} /> Poll next
              </Button>
            )}
            <Button variant="outline" onClick={() => replayFailed.mutate()} disabled={replayFailed.isPending}>
              <RefreshCw size={16} /> Replay failed
            </Button>
            <Button variant="outline" onClick={() => backfill.mutate()} disabled={backfill.isPending}>
              <History size={16} /> Backfill
            </Button>
          </div>
        }
      />

      {consumer && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Details</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Consumer ID</span>
                <span className="flex items-center gap-1">
                  <code className="font-mono text-xs">{consumer.id}</code>
                  <CopyButton text={consumer.id} />
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <Badge>{consumer.type}</Badge>
              </div>
              {consumer.type === "webhook" && (
                <>
                  <div className="flex justify-between gap-2">
                    <span className="text-muted-foreground">Endpoint</span>
                    <span className="max-w-[60%] truncate">{consumer.endpoint_url}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auto-complete</span>
                    {consumer.auto_complete ? (
                      <Badge className="border-emerald-500/30 text-emerald-400">on</Badge>
                    ) : (
                      <Badge className="border-amber-500/30 text-amber-400">off (await callback)</Badge>
                    )}
                  </div>
                  {Object.keys(consumer.custom_headers ?? {}).length > 0 && (
                    <div className="pt-1">
                      <div className="mb-1 text-muted-foreground">Custom headers</div>
                      <ul className="space-y-1">
                        {Object.keys(consumer.custom_headers).map((k) => (
                          <li key={k} className="rounded border border-border px-2 py-1 font-mono text-xs">
                            {k}: ••••••
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {consumer.routing_rules.length > 0 && (
                    <div className="pt-1">
                      <div className="mb-1 flex items-center justify-between text-muted-foreground">
                        <span>Filter rules</span>
                        <Badge>match {consumer.match_mode}</Badge>
                      </div>
                      <ul className="space-y-1">
                        {consumer.routing_rules.map((r, i) => (
                          <li key={i} className="rounded border border-border px-2 py-1 font-mono text-xs">
                            {r.field} {r.operator} {String(r.value)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span>{consumer.is_active ? "active" : "inactive"}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Usage</CardTitle></CardHeader>
            <CardContent>
              <Usage consumer={consumer} />
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Filter:</span>
            <Select value={status} onChange={(e) => { setStatus(e.target.value as DeliveryStatus | ""); setOffset(0); }} className="w-40">
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === "" ? "All statuses" : s}
                </option>
              ))}
            </Select>
            <Badge>{deliveriesQ.data?.total ?? 0} total</Badge>
          </div>

          {deliveriesQ.data && deliveriesQ.data.items.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH>Delivery</TH>
                  <TH>Status</TH>
                  <TH>Attempts</TH>
                  <TH>Remark</TH>
                  <TH>Updated</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {deliveriesQ.data.items.map((d) => (
                  <TR key={d.id}>
                    <TD className="font-mono text-xs">{shortId(d.id)}</TD>
                    <TD><StatusBadge status={d.status} /></TD>
                    <TD>{d.attempt_count}</TD>
                    <TD className="max-w-xs truncate text-muted-foreground">{d.last_remark ?? "—"}</TD>
                    <TD className="text-muted-foreground">{formatDate(d.updated_at ?? d.created_at)}</TD>
                    <TD>
                      <Link to={`/deliveries/${d.id}`}>
                        <Button variant="ghost" size="sm">History</Button>
                      </Link>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <p className="py-8 text-center text-muted-foreground">No deliveries.</p>
          )}
          <Pagination
            total={deliveriesQ.data?.total ?? 0}
            limit={LIMIT}
            offset={offset}
            onChange={setOffset}
          />
        </CardContent>
      </Card>

      {consumer && (
        <EditConsumerDialog
          open={editOpen}
          onClose={() => setEditOpen(false)}
          consumer={consumer}
          onDone={refetchConsumer}
        />
      )}
    </div>
  );
}

function EditConsumerDialog({
  open,
  onClose,
  consumer,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  consumer: Consumer;
  onDone: () => void;
}) {
  const [name, setName] = useState(consumer.name);
  const [endpoint, setEndpoint] = useState(consumer.endpoint_url ?? "");
  const [autoComplete, setAutoComplete] = useState(consumer.auto_complete);
  const [matchMode, setMatchMode] = useState<"any" | "all">(consumer.match_mode);
  const [secret, setSecret] = useState(consumer.signing_secret ?? "");
  const [rules, setRules] = useState<RoutingRule[]>(consumer.routing_rules ?? []);
  const [headers, setHeaders] = useState<{ key: string; value: string }[]>(
    Object.entries(consumer.custom_headers ?? {}).map(([key, value]) => ({ key, value }))
  );
  const isWebhook = consumer.type === "webhook";

  const addRule = () =>
    setRules((r) => [...r, { field: "payload.", operator: "equals", value: "" }]);
  const updateRule = (i: number, patch: Partial<RoutingRule>) =>
    setRules((r) => r.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
  const removeRule = (i: number) => setRules((r) => r.filter((_, idx) => idx !== i));

  const addHeader = () => setHeaders((h) => [...h, { key: "", value: "" }]);
  const updateHeader = (i: number, patch: Partial<{ key: string; value: string }>) =>
    setHeaders((h) => h.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
  const removeHeader = (i: number) => setHeaders((h) => h.filter((_, idx) => idx !== i));

  const save = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = { name };
      if (isWebhook) {
        body.endpoint_url = endpoint;
        body.auto_complete = autoComplete;
        body.match_mode = matchMode;
        body.signing_secret = secret || null;
        body.custom_headers = Object.fromEntries(
          headers.filter((h) => h.key.trim()).map((h) => [h.key.trim(), h.value])
        );
        body.routing_rules = rules
          .filter((r) => r.field)
          .map((r) => {
            const n = Number(r.value);
            return { ...r, value: r.value !== "" && !Number.isNaN(n) ? n : r.value };
          });
      }
      return api.patch(`/queues/${consumer.queue_id}/consumers/${consumer.id}`, body);
    },
    onSuccess: () => { toast.success("Consumer updated"); onDone(); onClose(); },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <Dialog open={open} onClose={onClose} title="Edit consumer" className="max-w-2xl">
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="space-y-4">
        <div className="space-y-1.5">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        {isWebhook && (
          <>
            <div className="space-y-1.5">
              <Label>Endpoint URL</Label>
              <Input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <Label>Signing secret (HMAC, optional)</Label>
              <Input value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="leave blank to disable" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={autoComplete} onChange={(e) => setAutoComplete(e.target.checked)} />
              Auto-complete on 2xx
            </label>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Custom headers</Label>
                <Button type="button" variant="ghost" size="sm" onClick={addHeader}><Plus size={14} /> Add</Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Sent on every POST for receiver-side validation. Reserved X-FlowQueue-*
                headers can’t be overridden.
              </p>
              {headers.map((h, i) => (
                <div key={i} className="grid grid-cols-12 items-center gap-2">
                  <Input className="col-span-5" placeholder="X-Api-Key" value={h.key}
                    onChange={(e) => updateHeader(i, { key: e.target.value })} />
                  <Input className="col-span-6" placeholder="value" value={h.value}
                    onChange={(e) => updateHeader(i, { value: e.target.value })} />
                  <Button type="button" variant="ghost" size="icon" className="col-span-1" onClick={() => removeHeader(i)}>
                    <Trash2 size={14} className="text-red-400" />
                  </Button>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Filter rules</Label>
                <Button type="button" variant="ghost" size="sm" onClick={addRule}><Plus size={14} /> Add</Button>
              </div>
              {rules.length > 0 && (
                <div className="flex items-center gap-2">
                  <Label>Match</Label>
                  <Select className="w-44" value={matchMode} onChange={(e) => setMatchMode(e.target.value as "any" | "all")}>
                    <option value="any">any rule (OR)</option>
                    <option value="all">all rules (AND)</option>
                  </Select>
                </div>
              )}
              {rules.map((r, i) => (
                <div key={i} className="grid grid-cols-12 items-center gap-2">
                  <Input className="col-span-5" placeholder="payload.country" value={r.field}
                    onChange={(e) => updateRule(i, { field: e.target.value })} />
                  <Select className="col-span-3" value={r.operator}
                    onChange={(e) => updateRule(i, { operator: e.target.value })}>
                    <option value="equals">equals</option>
                    <option value="not_equals">not_equals</option>
                    <option value="contains">contains</option>
                    <option value="greater_than">greater_than</option>
                    <option value="less_than">less_than</option>
                  </Select>
                  <Input className="col-span-3" placeholder="value" value={String(r.value ?? "")}
                    onChange={(e) => updateRule(i, { value: e.target.value })} />
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
          <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
        </div>
      </form>
    </Dialog>
  );
}
