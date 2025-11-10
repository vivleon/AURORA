"use client";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils"; // optional; swap to clsx if absent

// Lightweight toaster (no external deps). If shadcn/toast is available, replace with that.

type Toast = { id: number; title: string; desc?: string; tone?: "ok" | "warn" | "err" };

const ToastCtx = createContext<{
  push: (t: Omit<Toast, "id">) => void;
}>({ push: () => {} });

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(1);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = idRef.current++;
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((t) => (
          <div key={t.id} className={cn("rounded-xl border p-3 shadow bg-white/95 backdrop-blur", t.tone === "err" && "border-red-300", t.tone === "warn" && "border-yellow-300", t.tone === "ok" && "border-green-300") }>
            <div className="text-sm font-semibold">{t.title}</div>
            {t.desc && <div className="text-xs text-muted-foreground mt-1 max-w-[280px]">{t.desc}</div>}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
};

export function useToast() { return useContext(ToastCtx); }

// ---- EventStream hook (SSE) ----

type EventSummary = {
  id: number;
  ts: string;
  type: string;
  tool: string | null;
  intent: string | null;
  outcome: string | null;
  risk: string | null;
  latency_ms: number | null;
};

export function useEventStream(url = "/events/stream") {
  const { push } = useToast();
  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (evt) => {
      try {
        const e: EventSummary = JSON.parse(evt.data);
        const title = `${e.type}${e.tool ? ` · ${e.tool}` : ""}`;
        const tone = e.outcome === "error" ? "err" : e.outcome === "blocked" ? "warn" : "ok";
        const desc = `${e.intent || "(no-intent)"} • ${e.outcome || "unknown"} • ${e.latency_ms ?? "-"}ms`;
        push({ title, desc, tone });
      } catch {}
    };
    es.onerror = () => { /* keep silent; browser handles retry */ };
    return () => es.close();
  }, [url, push]);
}

// Convenience wrapper to drop into _app/layout
export const LiveEvents: React.FC = () => {
  useEventStream();
  return null;
};
