import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { copy } from "@/lib/utils";
import { cn } from "@/lib/utils";

/** Copy-on-click code block, marketing-styled (mirrors the dashboard SDK docs). */
export function CodeBlock({
  code,
  lang,
  className,
}: {
  code: string;
  lang?: string;
  className?: string;
}) {
  const [done, setDone] = useState(false);
  return (
    <div className={cn("group relative", className)}>
      {lang && (
        <span className="absolute left-3 top-2.5 select-none font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {lang}
        </span>
      )}
      <pre
        className={cn(
          "max-h-[30rem] overflow-auto rounded-xl border border-border bg-card/80 p-4 pr-12 font-mono text-[13px] leading-relaxed",
          lang && "pt-8"
        )}
      >
        <code>{code}</code>
      </pre>
      <button
        type="button"
        aria-label="Copy code"
        onClick={async () => {
          await copy(code);
          setDone(true);
          setTimeout(() => setDone(false), 1200);
        }}
        className="absolute right-2.5 top-2.5 rounded-md border border-border bg-background/70 p-1.5 text-muted-foreground opacity-0 transition hover:text-foreground group-hover:opacity-100"
      >
        {done ? <Check size={14} className="text-primary" /> : <Copy size={14} />}
      </button>
    </div>
  );
}
