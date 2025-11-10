"use client";
import React, { useEffect, useMemo, useState } from "react";
import { Separator } from "@/components/ui/separator";

// RAG Quality Panel
// Pulls /dash/rag/quality and /dash/rag/top-chunks, renders evidence rate + top docs table

interface QualityResp { evidence_rate: number }
interface TopRow { doc: string; chunk: number; hits: number }

const useFetch = <T,>(url: string, initial: T) => {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let c = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await fetch(url);
        if (!r.ok) throw new Error(await r.text());
        const j = await r.json();
        if (!c) setData(j);
      } catch (e: any) {
        if (!c) setError(e?.message ?? "fetch failed");
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => { c = true };
  }, [url]);
  return { data, loading, error } as const;
};

function isUrl(s: string): boolean { return /^(https?:)?\/\//i.test(s); }

export default function RagPanel() {
  const q = useFetch<QualityResp>(`/dash/rag/quality?window=24h`, { evidence_rate: 0 }, []);
  const rows = useFetch<{ rows: TopRow[] }>(`/dash/rag/top-chunks?window=24h&limit=20`, { rows: [] }, []);

  return (
    <div className="rounded-2xl border p-4 space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Evidence Attachment Rate (24h)</div>
          <div className="text-2xl font-semibold">{(q.data.evidence_rate * 100).toFixed(1)}%</div>
        </div>
      </div>
      <Separator />
      <div>
        <div className="font-semibold mb-2">Top Evidence Chunks</div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-2 pr-3">Document</th>
                <th className="py-2 pr-3">Chunk</th>
                <th className="py-2 pr-3">Hits</th>
                <th className="py-2">Link</th>
              </tr>
            </thead>
            <tbody>
              {rows.data.rows.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="py-2 pr-3 truncate max-w-[360px]" title={r.doc}>{r.doc}</td>
                  <td className="py-2 pr-3">{r.chunk}</td>
                  <td className="py-2 pr-3">{r.hits}</td>
                  <td className="py-2">
                    {isUrl(r.doc) ? (
                      <a href={r.doc} className="underline" target="_blank" rel="noreferrer">Open</a>
                    ) : (
                      <a href={`/docs/${encodeURIComponent(r.doc)}?chunk=${r.chunk}`} className="underline" target="_blank" rel="noreferrer">Preview</a>
                    )}
                  </td>
                </tr>
              ))}
              {!rows.data.rows.length && (
                <tr><td className="py-4 text-muted-foreground" colSpan={4}>No data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
