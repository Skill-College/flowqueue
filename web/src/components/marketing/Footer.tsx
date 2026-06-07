import { Link } from "react-router-dom";
import { Logo } from "@/components/Logo";

const cols = [
  {
    title: "Product",
    links: [
      { to: "/about", label: "About" },
      { to: "/pricing", label: "Pricing" },
      { to: "/feedback", label: "Feedback" },
    ],
  },
  {
    title: "Developers",
    links: [
      { to: "/docs/sdk", label: "Python SDK" },
      { to: "/docs/api", label: "HTTP API" },
      { to: "/docs", label: "OpenAPI", external: true },
    ],
  },
  {
    title: "Account",
    links: [
      { to: "/login", label: "Sign in" },
      { to: "/register", label: "Start free" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-card/40">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 sm:grid-cols-2 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <Logo size={30} animated={false} />
          <p className="mt-4 max-w-xs text-sm text-muted-foreground">
            Durable, Postgres-backed message queues with fan-out, replay and webhooks.
          </p>
          <span className="mt-4 inline-block rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            Free during beta
          </span>
        </div>

        {cols.map((c) => (
          <div key={c.title}>
            <h4 className="mb-3 text-sm font-semibold">{c.title}</h4>
            <ul className="space-y-2">
              {c.links.map((l) =>
                "external" in l && l.external ? (
                  <li key={l.label}>
                    <a
                      href={l.to}
                      className="text-sm text-muted-foreground transition hover:text-foreground"
                    >
                      {l.label}
                    </a>
                  </li>
                ) : (
                  <li key={l.label}>
                    <Link
                      to={l.to}
                      className="text-sm text-muted-foreground transition hover:text-foreground"
                    >
                      {l.label}
                    </Link>
                  </li>
                )
              )}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} FlowQueue. All rights reserved.
      </div>
    </footer>
  );
}
