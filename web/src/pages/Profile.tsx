import { useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div>
      <PageHeader title="Profile" description="Your account" />
      <Card className="max-w-lg">
        <CardHeader><CardTitle>Account</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Role</span>
            {user?.role === "admin" ? (
              <Badge className="border-primary/40 text-primary">admin</Badge>
            ) : (
              <span>user</span>
            )}
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Member since</span>
            <span>{formatDate(user?.created_at)}</span>
          </div>
          <div className="pt-2">
            <Button
              variant="outline"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              <LogOut size={16} /> Sign out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
