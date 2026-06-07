import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Page, User } from "@/lib/types";
import { PageHeader } from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

export function AdminUsers() {
  const { data } = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => (await api.get<Page<User>>("/admin/users", { params: { limit: 100 } })).data,
  });

  return (
    <div>
      <PageHeader title="Users" description="All accounts (admin view)" />
      <Card>
        <CardContent className="pt-6">
          <Table>
            <THead>
              <TR>
                <TH>Email</TH>
                <TH>Role</TH>
                <TH>Status</TH>
                <TH>Created</TH>
              </TR>
            </THead>
            <TBody>
              {(data?.items ?? []).map((u) => (
                <TR key={u.id}>
                  <TD className="font-medium">{u.email}</TD>
                  <TD>
                    {u.role === "admin" ? (
                      <Badge className="border-primary/40 text-primary">admin</Badge>
                    ) : (
                      <span className="text-muted-foreground">user</span>
                    )}
                  </TD>
                  <TD>{u.is_active ? <span className="text-emerald-400">active</span> : <span className="text-muted-foreground">disabled</span>}</TD>
                  <TD className="text-muted-foreground">{formatDate(u.created_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
