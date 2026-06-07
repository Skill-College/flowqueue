import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import type { DeliveryStatus } from "@/lib/types";

const statusStyles: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  processing: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  completed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  running: "bg-sky-500/15 text-sky-400 border-sky-500/30",
};

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-medium",
        className
      )}
      {...props}
    />
  );
}

export function StatusBadge({ status }: { status: DeliveryStatus | string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        statusStyles[status] ?? "bg-secondary text-secondary-foreground border-border"
      )}
    >
      {status}
    </span>
  );
}
