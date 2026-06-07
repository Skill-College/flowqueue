import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Feedback, FeedbackCategory, Page } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

const categoryStyle: Record<FeedbackCategory, string> = {
  bug: "border-destructive/40 text-destructive",
  feature: "border-primary/40 text-primary",
  general: "border-border text-muted-foreground",
};

export function AdminFeedback() {
  const { data } = useQuery({
    queryKey: ["admin-feedback"],
    queryFn: async () =>
      (await api.get<Page<Feedback>>("/feedback", { params: { limit: 100 } })).data,
  });

  const items = data?.items ?? [];

  return (
    <div>
      <PageHeader
        title="Feedback"
        description="Product feedback submitted from the website (admin view)"
      />
      <Card>
        <CardContent className="pt-6">
          {items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No feedback yet.</p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>From</TH>
                  <TH>Category</TH>
                  <TH>Message</TH>
                  <TH>Received</TH>
                </TR>
              </THead>
              <TBody>
                {items.map((f) => (
                  <TR key={f.id}>
                    <TD className="align-top">
                      <div className="font-medium">{f.name || "—"}</div>
                      <a
                        href={`mailto:${f.email}`}
                        className="text-xs text-primary hover:underline"
                      >
                        {f.email}
                      </a>
                    </TD>
                    <TD className="align-top">
                      <Badge className={categoryStyle[f.category]}>{f.category}</Badge>
                    </TD>
                    <TD className="max-w-md align-top">
                      <p className="whitespace-pre-wrap text-sm">{f.message}</p>
                    </TD>
                    <TD className="align-top text-muted-foreground">
                      {formatDate(f.created_at)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
