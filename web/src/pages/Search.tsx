import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Delivery, DeliveryStatus, Message, Page } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { Select } from "@/components/ui/select";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { Pagination } from "@/components/ui/pagination";
import { formatDate, shortId } from "@/lib/utils";

const STATUSES: (DeliveryStatus | "")[] = ["", "pending", "processing", "completed", "failed", "dead"];
const LIMIT = 25;

export function Search() {
  const [tab, setTab] = useState<"messages" | "deliveries">("messages");
  const [status, setStatus] = useState<DeliveryStatus | "">("");
  const [offset, setOffset] = useState(0);

  const msgs = useQuery({
    queryKey: ["search-messages", status, offset],
    queryFn: async () =>
      (
        await api.get<Page<Message>>("/search/messages", {
          params: { limit: LIMIT, offset, ...(status ? { status } : {}) },
        })
      ).data,
    enabled: tab === "messages",
  });
  const dels = useQuery({
    queryKey: ["search-deliveries", status, offset],
    queryFn: async () =>
      (
        await api.get<Page<Delivery>>("/search/deliveries", {
          params: { limit: LIMIT, offset, ...(status ? { status } : {}) },
        })
      ).data,
    enabled: tab === "deliveries",
  });

  const data = tab === "messages" ? msgs.data : dels.data;

  return (
    <div>
      <PageHeader title="Search" description="Find messages and deliveries across your queues" />
      <div className="mb-4 flex items-center gap-3">
        <Tabs
          active={tab}
          onChange={(t) => { setTab(t as "messages" | "deliveries"); setOffset(0); }}
          tabs={[
            { id: "messages", label: "Messages" },
            { id: "deliveries", label: "Deliveries" },
          ]}
        />
        <Select value={status} onChange={(e) => { setStatus(e.target.value as DeliveryStatus | ""); setOffset(0); }} className="w-44">
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s === "" ? "All statuses" : s}</option>
          ))}
        </Select>
        <Badge>{data?.total ?? 0} results</Badge>
      </div>

      <Card>
        <CardContent className="pt-6">
          {tab === "messages" ? (
            (msgs.data?.items.length ?? 0) > 0 ? (
              <Table>
                <THead><TR><TH>Seq</TH><TH>Queue</TH><TH>Payload</TH><TH>Published</TH></TR></THead>
                <TBody>
                  {msgs.data!.items.map((m) => (
                    <TR key={m.id}>
                      <TD className="font-mono">{m.sequence_num}</TD>
                      <TD>
                        <Link to={`/queues/${m.queue_id}`} className="text-primary hover:underline">
                          {shortId(m.queue_id)}
                        </Link>
                      </TD>
                      <TD className="max-w-md truncate font-mono text-xs text-muted-foreground">
                        {JSON.stringify(m.payload)}
                      </TD>
                      <TD className="text-muted-foreground">{formatDate(m.published_at)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : <p className="py-8 text-center text-muted-foreground">No messages.</p>
          ) : (dels.data?.items.length ?? 0) > 0 ? (
            <Table>
              <THead><TR><TH>Delivery</TH><TH>Status</TH><TH>Attempts</TH><TH>Updated</TH></TR></THead>
              <TBody>
                {dels.data!.items.map((d) => (
                  <TR key={d.id}>
                    <TD className="font-mono text-xs">
                      <Link to={`/deliveries/${d.id}`} className="text-primary hover:underline">{shortId(d.id)}</Link>
                    </TD>
                    <TD><StatusBadge status={d.status} /></TD>
                    <TD>{d.attempt_count}</TD>
                    <TD className="text-muted-foreground">{formatDate(d.updated_at ?? d.created_at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : <p className="py-8 text-center text-muted-foreground">No deliveries.</p>}
          <Pagination total={data?.total ?? 0} limit={LIMIT} offset={offset} onChange={setOffset} />
        </CardContent>
      </Card>
    </div>
  );
}
