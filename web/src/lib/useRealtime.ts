import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "./api";

/**
 * Subscribe to the server's SSE event stream and invalidate live queries on any
 * delivery event, so dashboards/lists update in near-realtime without manual refresh.
 */
export function useRealtime() {
  const qc = useQueryClient();
  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    const es = new EventSource(
      `/api/v1/events/stream?access_token=${encodeURIComponent(token)}`
    );
    let timer: ReturnType<typeof setTimeout> | null = null;
    es.onmessage = () => {
      // Debounce bursts of events into a single invalidation sweep.
      if (timer) return;
      timer = setTimeout(() => {
        timer = null;
        qc.invalidateQueries({ queryKey: ["queue-stats"] });
        qc.invalidateQueries({ queryKey: ["deliveries"] });
        qc.invalidateQueries({ queryKey: ["dlq"] });
        qc.invalidateQueries({ queryKey: ["queues"] });
      }, 400);
    };
    es.onerror = () => {
      /* EventSource auto-reconnects; nothing to do */
    };
    return () => {
      if (timer) clearTimeout(timer);
      es.close();
    };
  }, [qc]);
}
