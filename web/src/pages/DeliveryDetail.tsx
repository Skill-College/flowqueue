import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CircleSlash, MessageSquarePlus, PlayCircle } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import type { Delivery, DeliveryLog } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { JsonView } from "@/components/JsonView";
import { formatDate, shortId } from "@/lib/utils";

const eventColors: Record<string, string> = {
  created: "bg-primary",
  acknowledged: "bg-sky-400",
  status_updated: "bg-emerald-400",
  retry_scheduled: "bg-amber-400",
  replayed: "bg-violet-400",
  remark_added: "bg-muted-foreground",
};

export function DeliveryDetail() {
  const { deliveryId = "" } = useParams();
  const qc = useQueryClient();

  const deliveryQ = useQuery({
    queryKey: ["delivery", deliveryId],
    queryFn: async () => (await api.get<Delivery>(`/deliveries/${deliveryId}`)).data,
  });
  const historyQ = useQuery({
    queryKey: ["delivery-history", deliveryId],
    queryFn: async () => (await api.get<DeliveryLog[]>(`/deliveries/${deliveryId}/history`)).data,
  });

  const d = deliveryQ.data;

  const refetch = () => {
    qc.invalidateQueries({ queryKey: ["delivery", deliveryId] });
    qc.invalidateQueries({ queryKey: ["delivery-history", deliveryId] });
  };

  function actionMutation(fn: () => Promise<unknown>, label: string) {
    return {
      mutationFn: fn,
      onSuccess: () => {
        toast.success(label);
        refetch();
      },
      onError: (e: unknown) => toast.error(apiErrorMessage(e)),
    };
  }

  const ack = useMutation(
    actionMutation(() => api.post(`/deliveries/${deliveryId}/ack`), "Acknowledged")
  );
  const complete = useMutation(
    actionMutation(
      () => api.post(`/deliveries/${deliveryId}/complete`, { remark: "completed via UI" }),
      "Completed"
    )
  );
  const fail = useMutation(
    actionMutation(
      () => api.post(`/deliveries/${deliveryId}/fail`, { remark: "failed via UI", metadata: {} }),
      "Marked failed"
    )
  );
  const remark = useMutation({
    mutationFn: async () => {
      const text = window.prompt("Remark");
      if (!text) throw new Error("Cancelled");
      return api.post(`/deliveries/${deliveryId}/remark`, { remark: text });
    },
    onSuccess: () => {
      toast.success("Remark added");
      refetch();
    },
    onError: (e) => {
      const msg = apiErrorMessage(e);
      if (msg !== "Cancelled") toast.error(msg);
    },
  });

  return (
    <div>
      <PageHeader
        title="Delivery"
        description={d ? `${shortId(d.id)} · attempt ${d.attempt_count}` : ""}
        action={
          d && (
            <div className="flex flex-wrap gap-2">
              {(d.status === "pending" || d.status === "processing") && (
                <Button variant="outline" onClick={() => ack.mutate()}>
                  <PlayCircle size={16} /> Ack
                </Button>
              )}
              {d.status !== "completed" && (
                <Button variant="outline" onClick={() => complete.mutate()}>
                  <Check size={16} /> Complete
                </Button>
              )}
              {d.status !== "completed" && (
                <Button variant="outline" onClick={() => fail.mutate()}>
                  <CircleSlash size={16} /> Fail
                </Button>
              )}
              <Button variant="outline" onClick={() => remark.mutate()}>
                <MessageSquarePlus size={16} /> Remark
              </Button>
            </div>
          )
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Status</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">State</span>
              {d && <StatusBadge status={d.status} />}
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Attempts</span>
              <span>{d?.attempt_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last remark</span>
              <span className="max-w-[55%] truncate">{d?.last_remark ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Completed</span>
              <span>{formatDate(d?.completed_at)}</span>
            </div>
            {d && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Consumer</span>
                <Link to={`/consumers/${d.consumer_id}`} className="text-primary hover:underline">
                  {shortId(d.consumer_id)}
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Audit timeline</CardTitle></CardHeader>
          <CardContent>
            <ol className="relative space-y-5 border-l border-border pl-5">
              {(historyQ.data ?? []).map((log) => (
                <li key={log.id} className="relative">
                  <span
                    className={`absolute -left-[1.42rem] top-1 h-2.5 w-2.5 rounded-full ${
                      eventColors[log.event_type] ?? "bg-muted-foreground"
                    }`}
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium capitalize">{log.event_type.replace(/_/g, " ")}</span>
                    {log.from_status && log.to_status && (
                      <span className="text-xs text-muted-foreground">
                        {log.from_status} → {log.to_status}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">{formatDate(log.created_at)}</span>
                  </div>
                  {log.remark && <p className="mt-1 text-sm text-muted-foreground">{log.remark}</p>}
                  {Object.keys(log.context ?? {}).length > 0 && (
                    <JsonView data={log.context} className="mt-2 max-h-40" />
                  )}
                </li>
              ))}
              {historyQ.data?.length === 0 && (
                <li className="text-sm text-muted-foreground">No events.</li>
              )}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
