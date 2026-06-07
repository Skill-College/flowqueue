import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Pagination({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
      <span>
        {from}–{to} of {total}
      </span>
      <div className="flex gap-1">
        <Button
          size="sm"
          variant="outline"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft size={14} /> Prev
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={to >= total}
          onClick={() => onChange(offset + limit)}
        >
          Next <ChevronRight size={14} />
        </Button>
      </div>
    </div>
  );
}
