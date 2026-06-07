import { type ReactNode } from "react";
import { Reveal } from "@/components/marketing/Reveal";

/** Two-column docs layout: sticky in-page nav + content. Shared by SDK & API docs. */
export function DocsShell({
  title,
  subtitle,
  sections,
  action,
  children,
}: {
  title: string;
  subtitle: string;
  sections: { id: string; label: string }[];
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:py-20">
      <Reveal className="mb-10 flex flex-col gap-4 border-b border-border pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="mb-3 inline-block rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary">
            Docs
          </span>
          <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
          <p className="mt-3 max-w-2xl text-muted-foreground">{subtitle}</p>
        </div>
        {action}
      </Reveal>

      <div className="grid gap-10 lg:grid-cols-[200px_1fr]">
        <aside className="hidden lg:block">
          <nav className="sticky top-24 space-y-1">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="block rounded-lg px-3 py-1.5 text-sm text-muted-foreground transition hover:bg-secondary hover:text-foreground"
              >
                {s.label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="min-w-0 space-y-14">{children}</div>
      </div>
    </div>
  );
}

export function DocSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <Reveal>
      <section id={id} className="scroll-mt-24 space-y-4">
        <h2 className="font-display text-2xl font-bold tracking-tight">{title}</h2>
        {children}
      </section>
    </Reveal>
  );
}
