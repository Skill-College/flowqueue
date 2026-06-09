import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ArrowRight, Archive, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import type { Page, Queue } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

export function Queues() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"active" | "archived">("active");
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [fifo, setFifo] = useState(false);
  const [maxRetries, setMaxRetries] = useState(3);
  const [retryDelay, setRetryDelay] = useState(60);
  const [visibility, setVisibility] = useState(30);
  const [retention, setRetention] = useState(604800);
  const [successRetention, setSuccessRetention] = useState(86400);
  const [failedRetention, setFailedRetention] = useState(604800);
  const [dlqEnabled, setDlqEnabled] = useState(true);
  const [metadataText, setMetadataText] = useState("");

  const archived = tab === "archived";
  const { data, isLoading } = useQuery({
    queryKey: ["queues", tab],
    queryFn: async () =>
      (await api.get<Page<Queue>>("/queues", { params: { limit: 100, archived } })).data,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["queues"] });

  const create = useMutation({
    mutationFn: async () => {
      let metadata: Record<string, unknown> = {};
      if (metadataText.trim()) {
        try {
          metadata = JSON.parse(metadataText);
        } catch {
          throw new Error("Metadata is not valid JSON");
        }
      }
      return (
        await api.post<Queue>("/queues", {
          name,
          fifo_enabled: fifo,
          max_retries: maxRetries,
          retry_delay_seconds: retryDelay,
          visibility_timeout_seconds: visibility,
          retention_seconds: retention,
          success_retention_seconds: successRetention,
          failed_retention_seconds: failedRetention,
          dlq_enabled: dlqEnabled,
          metadata,
        })
      ).data;
    },
    onSuccess: () => {
      toast.success("Queue created");
      invalidate();
      setOpen(false);
      setName("");
      setMetadataText("");
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const archive = useMutation({
    mutationFn: async (id: string) => api.delete(`/queues/${id}`),
    onSuccess: () => {
      toast.success("Queue archived");
      invalidate();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const restore = useMutation({
    mutationFn: async (id: string) => api.patch(`/queues/${id}`, { is_active: true }),
    onSuccess: () => {
      toast.success("Queue restored");
      invalidate();
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Queues"
        description="Channels that own messages and consumers"
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New queue
          </Button>
        }
      />

      <Tabs
        className="mb-4"
        active={tab}
        onChange={(t) => setTab(t as "active" | "archived")}
        tabs={[
          { id: "active", label: "Active" },
          { id: "archived", label: "Archived" },
        ]}
      />

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : data && data.items.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Mode</TH>
                  <TH>Retries</TH>
                  <TH>Created</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {data.items.map((q) => (
                  <TR key={q.id}>
                    <TD className="font-medium">{q.name}</TD>
                    <TD>{q.fifo_enabled ? <Badge>FIFO</Badge> : <span className="text-muted-foreground">standard</span>}</TD>
                    <TD>{q.max_retries}</TD>
                    <TD className="text-muted-foreground">{formatDate(q.created_at)}</TD>
                    <TD>
                      <div className="flex justify-end gap-1">
                        <Link to={`/queues/${q.id}`}>
                          <Button variant="ghost" size="sm">
                            Open <ArrowRight size={14} />
                          </Button>
                        </Link>
                        {archived ? (
                          <Button variant="ghost" size="sm" onClick={() => restore.mutate(q.id)}>
                            <RotateCcw size={14} /> Restore
                          </Button>
                        ) : (
                          <Button variant="ghost" size="sm" onClick={() => archive.mutate(q.id)}>
                            <Archive size={14} className="text-amber-500" /> Archive
                          </Button>
                        )}
                      </div>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <p className="text-muted-foreground">
                {archived ? "No archived queues." : "No queues yet."}
              </p>
              {!archived && (
                <Button onClick={() => setOpen(true)}>
                  <Plus size={16} /> Create your first queue
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} title="New queue" description="Create a message queue" className="max-w-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-1.5">
            <Label htmlFor="qn">Name</Label>
            <Input id="qn" value={name} onChange={(e) => setName(e.target.value)} placeholder="orders" required autoFocus />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="mr">Max retries</Label>
              <Input id="mr" type="number" min={0} value={maxRetries} onChange={(e) => setMaxRetries(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">Max total delivery attempts.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rd">Retry delay (s)</Label>
              <Input id="rd" type="number" min={0} value={retryDelay} onChange={(e) => setRetryDelay(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">Wait before a retry becomes visible.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="vt">Visibility timeout (s)</Label>
              <Input id="vt" type="number" min={1} value={visibility} onChange={(e) => setVisibility(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">In-flight time before auto-reclaim.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rt">Pending retention (s)</Label>
              <Input id="rt" type="number" min={1} value={retention} onChange={(e) => setRetention(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">Un-consumed messages. Default 604800 = 7 days.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sr">Success retention (s)</Label>
              <Input id="sr" type="number" min={1} value={successRetention} onChange={(e) => setSuccessRetention(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">Completed messages. Default 86400 = 24 hours.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="fr">Failed retention (s)</Label>
              <Input id="fr" type="number" min={1} value={failedRetention} onChange={(e) => setFailedRetention(Number(e.target.value))} />
              <p className="text-xs text-muted-foreground">Failed/dead messages. Default 604800 = 7 days.</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={fifo} onChange={(e) => setFifo(e.target.checked)} />
              FIFO ordering
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={dlqEnabled} onChange={(e) => setDlqEnabled(e.target.checked)} />
              Dead-letter enabled
            </label>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="md">Metadata (JSON, optional)</Label>
            <Textarea id="md" value={metadataText} onChange={(e) => setMetadataText(e.target.value)} placeholder='{"team":"payments"}' rows={3} />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
