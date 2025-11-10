"use client";
import React, { useEffect } from "react";
import { toast as toastFn } from "sonner"; // shadcn recommends 'sonner' for toasts

// If your template already has <Toaster /> mounted globally, keep it there.
// Otherwise, export ToasterMount to include once at root.

export const ToasterMount = () => <></>; // placeholder; ensure <Toaster/> is in RootLayout

export type EventSummary = {
  id?: number;
  ts?: string;
  type?: string;
  tool?: string | null;
  intent?: string | null;
  outcome?: string | null;
  risk?: string | null;
  latency_ms?: number | null;
};

export function useEventStreamShadcn(url = "/events/stream") {
  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (evt) => {
      try {
        const e: EventSummary = JSON.parse(evt.data);
        const title = `${e.type}${e.tool ? ` · ${e.tool}` : ""}`;
        const desc = `${e.intent || "(no-intent)"} • ${e.outcome || "unknown"} • ${e.latency_ms ?? "-"}ms`;
        toastFn(title, { description: desc });
      } catch {}
    };
    es.onerror = () => {};
    return () => es.close();
  }, [url]);
}

export const LiveEventsShadcn: React.FC = () => {
  useEventStreamShadcn();
  return null;
};
