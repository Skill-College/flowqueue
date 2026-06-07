import { type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ListChecks,
  KeyRound,
  Users,
  LogOut,
  Sun,
  Moon,
  Search as SearchIcon,
  BookOpen,
  MessageSquare,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { useRealtime } from "@/lib/useRealtime";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/Logo";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/queues", label: "Queues", icon: ListChecks, end: false },
  { to: "/search", label: "Search", icon: SearchIcon, end: false },
  { to: "/api-keys", label: "API Keys", icon: KeyRound, end: false },
  { to: "/sdk", label: "SDK", icon: BookOpen, end: false },
];

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  useRealtime();

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/50 md:flex">
        <Link to="/dashboard" className="flex items-center px-5 py-5">
          <Logo size={30} animated={false} textClassName="text-lg" />
        </Link>
        <nav className="flex-1 space-y-1 px-3 py-2">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <n.icon size={18} />
              {n.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin/users"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <Users size={18} />
              Users
            </NavLink>
          )}
          {user?.role === "admin" && (
            <NavLink
              to="/admin/feedback"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <MessageSquare size={18} />
              Feedback
            </NavLink>
          )}
        </nav>
        <div className="border-t border-border p-3">
          <Link to="/profile" className="mb-2 block rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent">
            <div className="truncate font-medium text-foreground">{user?.email}</div>
            <div className="capitalize">{user?.role}</div>
          </Link>
          <Button
            variant="ghost"
            size="sm"
            className="mb-1 w-full justify-start text-muted-foreground"
            onClick={toggle}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut size={16} /> Sign out
          </Button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
