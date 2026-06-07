import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import type { ApiKey, ApiKeyCreated } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

export function ApiKeys() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const { data } = useQuery({
    queryKey: ["api-keys"],
    queryFn: async () => (await api.get<ApiKey[]>("/api-keys")).data,
  });

  const [scopes, setScopes] = useState<string[]>(["publish", "consume"]);
  const toggleScope = (s: string) =>
    setScopes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const create = useMutation({
    mutationFn: async () => (await api.post<ApiKeyCreated>("/api-keys", { name, scopes })).data,
    onSuccess: (key) => {
      setCreated(key);
      setOpen(false);
      setName("");
      setScopes(["publish", "consume"]);
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const revoke = useMutation({
    mutationFn: async (id: string) => api.delete(`/api-keys/${id}`),
    onSuccess: () => {
      toast.success("Key revoked");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="API Keys"
        description="Programmatic access tokens scoped to your account"
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New key
          </Button>
        }
      />

      <Card>
        <CardContent className="pt-6">
          {data && data.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Prefix</TH>
                  <TH>Scopes</TH>
                  <TH>Status</TH>
                  <TH>Last used</TH>
                  <TH>Created</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {data.map((k) => (
                  <TR key={k.id}>
                    <TD className="font-medium">{k.name}</TD>
                    <TD className="font-mono text-xs text-muted-foreground">{k.prefix}…</TD>
                    <TD className="text-xs text-muted-foreground">{k.scopes.join(", ")}</TD>
                    <TD>
                      {k.is_active ? (
                        <Badge className="border-emerald-500/30 text-emerald-400">active</Badge>
                      ) : (
                        <span className="text-muted-foreground">revoked</span>
                      )}
                    </TD>
                    <TD className="text-muted-foreground">{formatDate(k.last_used_at)}</TD>
                    <TD className="text-muted-foreground">{formatDate(k.created_at)}</TD>
                    <TD>
                      {k.is_active && (
                        <Button variant="ghost" size="sm" onClick={() => revoke.mutate(k.id)}>
                          <Trash2 size={14} className="text-red-400" />
                        </Button>
                      )}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <p className="py-8 text-center text-muted-foreground">No API keys yet.</p>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} title="New API key">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="production-publisher" required autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label>Scopes</Label>
            <div className="flex gap-4">
              {["publish", "consume", "admin"].map((s) => (
                <label key={s} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={scopes.includes(s)} onChange={() => toggleScope(s)} />
                  {s}
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={!!created}
        onClose={() => setCreated(null)}
        title="API key created"
        description="Copy it now — it will never be shown again."
      >
        <div className="space-y-3">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-background p-3">
            <code className="flex-1 break-all font-mono text-sm">{created?.token}</code>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => {
                navigator.clipboard.writeText(created?.token ?? "");
                setCopied(true);
                toast.success("Copied");
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
            </Button>
          </div>
          <div className="flex justify-end">
            <Button onClick={() => setCreated(null)}>Done</Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
