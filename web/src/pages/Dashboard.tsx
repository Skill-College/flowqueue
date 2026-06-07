import { useQuery, useQueries } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Inbox, CheckCircle2, XCircle, Loader2, ListChecks } from "lucide-react";
import api from "@/lib/api";
import type { Page, Queue, QueueStats } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function StatCard({
  label,
  value,
  icon: Icon,
  tint,
}: {
  label: string;
  value: number | string;
  icon: typeof Inbox;
  tint: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tint}`}>
          <Icon size={20} />
        </div>
        <div>
          <div className="text-2xl font-semibold">{value}</div>
          <div className="text-sm text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const queuesQ = useQuery({
    queryKey: ["queues", "all"],
    queryFn: async () => (await api.get<Page<Queue>>("/queues", { params: { limit: 100 } })).data,
  });

  const queues = queuesQ.data?.items ?? [];

  const statsQ = useQueries({
    queries: queues.map((q) => ({
      queryKey: ["queue-stats", q.id],
      queryFn: async () => (await api.get<QueueStats>(`/queues/${q.id}/stats`)).data,
      enabled: queues.length > 0,
    })),
  });

  const allStats = statsQ.map((s) => s.data).filter(Boolean) as QueueStats[];
  const sum = (k: keyof QueueStats) =>
    allStats.reduce((acc, s) => acc + (Number(s[k]) || 0), 0);

  const chartData = queues.map((q, i) => ({
    name: q.name.length > 12 ? q.name.slice(0, 12) + "…" : q.name,
    pending: allStats[i]?.pending ?? 0,
    completed: allStats[i]?.completed ?? 0,
    failed: allStats[i]?.failed ?? 0,
  }));

  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of your queues and deliveries" />

      {queuesQ.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Queues" value={queues.length} icon={ListChecks} tint="bg-primary/15 text-primary" />
          <StatCard label="Pending" value={sum("pending")} icon={Inbox} tint="bg-amber-500/15 text-amber-400" />
          <StatCard label="Completed" value={sum("completed")} icon={CheckCircle2} tint="bg-emerald-500/15 text-emerald-400" />
          <StatCard label="Failed" value={sum("failed")} icon={XCircle} tint="bg-red-500/15 text-red-400" />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Deliveries by queue</CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                No queues yet — create one to see metrics.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="pending" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="completed" stackId="a" fill="#10b981" />
                  <Bar dataKey="failed" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Processing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <StatCard label="In flight" value={sum("processing")} icon={Loader2} tint="bg-sky-500/15 text-sky-400" />
            <div>
              <div className="mb-2 text-sm font-medium text-muted-foreground">Your queues</div>
              <div className="space-y-1">
                {queues.slice(0, 6).map((q) => (
                  <Link
                    key={q.id}
                    to={`/queues/${q.id}`}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-accent"
                  >
                    <span className="truncate">{q.name}</span>
                    <span className="text-muted-foreground">{q.is_active ? "active" : "inactive"}</span>
                  </Link>
                ))}
                {queues.length === 0 && (
                  <div className="text-sm text-muted-foreground">No queues.</div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
