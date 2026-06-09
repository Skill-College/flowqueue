import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function relativeTime(value?: string | null): string {
  if (!value) return "—";
  const diff = Date.now() - new Date(value).getTime();
  const s = Math.round(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

export function shortId(id?: string | null): string {
  if (!id) return "—";
  return id.slice(0, 8);
}

export async function copy(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

const RESERVED_HEADER_PREFIX = /^X-FlowQueue-/i;
const INVALID_HEADER_CHARS = /[\r\n:]/;

/**
 * Build the custom_headers map from key/value rows: drops blank keys, trims
 * key+value, and rejects reserved (X-FlowQueue-*) or malformed headers.
 * Throws Error with a friendly message on the first invalid entry.
 */
export function buildCustomHeaders(
  rows: { key: string; value: string }[]
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (!key) continue;
    if (RESERVED_HEADER_PREFIX.test(key)) {
      throw new Error(`Reserved header can't be set: ${key}`);
    }
    if (INVALID_HEADER_CHARS.test(key) || INVALID_HEADER_CHARS.test(row.value)) {
      throw new Error(`Invalid characters in header: ${key}`);
    }
    out[key] = row.value.trim();
  }
  return out;
}
