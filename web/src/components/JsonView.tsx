import { cn } from "@/lib/utils";

export function JsonView({ data, className }: { data: unknown; className?: string }) {
  return (
    <pre
      className={cn(
        "max-h-80 overflow-auto rounded-lg border border-border bg-background/60 p-3 text-xs leading-relaxed text-muted-foreground",
        className
      )}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
