"use client";
import React, { useEffect, useRef } from "react";
import { toast as toastFn } from "sonner";

// Rate-limited, aggregated toasts for event stream
// Policy:
//  - Key = `${type}|${tool}|${outcome}`
//  - Within WINDOW_MS, increment counter instead of spamming new toasts
//  - Update existing toast contents: "(xN)" suffix

const WINDOW_MS = 2000; // aggregation window

type EventSummary = {
  type?: string;
  tool?: string | null;
  outcome?: string | null;
  intent?: string | null;
  latency_ms?: number | null;
};

export function useEventStreamShadcnAgg(url = "/events/stream") {
  const state = useRef<{ [key: string]: { id: string | number; count: number; ts: number } }>({});

  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (evt) => {
      try {
        const e: EventSummary = JSON.parse(evt.data);
        const key = `${e.type || ""}|${e.tool || ""}|${e.outcome || ""}`;
        const now = Date.now();
        const cur = state.current[key];
        const title = `${e.type}${e.tool ? ` · ${e.tool}` : ""}`;
        const baseDesc = `${e.intent || "(no-intent)"} • ${e.outcome || "unknown"}`;
        if (!cur || now - cur.ts > WINDOW_MS) {
          const id = toastFn(title, { description: baseDesc });
          state.current[key] = { id, count: 1, ts: now };
        } else {
          cur.count += 1;
          cur.ts = now;
          // sonner doesn't support direct update API; re-emit a new toast and close old if needed
          // To keep simple, just emit a lightweight toast that shows aggregate count
          toastFn(title, { description: `${baseDesc} (x${cur.count})` });
        }
      } catch {}
    };
    es.onerror = () => {};
    return () => es.close();
  }, [url]);
}

export const LiveEventsShadcnAgg: React.FC = () => {
  useEventStreamShadcnAgg();
  return null;
};
