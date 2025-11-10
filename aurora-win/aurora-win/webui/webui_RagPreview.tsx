"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

// RAG Preview UI with highlight + prev/next navigation
// Requires rag_preview_router mounted on backend

type ChunkResp = {
  doc_id: string;
  chunk: number;
  start: number;
  end: number;
  text: string;
  highlights: { term: string; positions: number[] }[];
};

type SearchResp = { doc_id: string; term: string; chunks: number[] };

export default function RagPreview({ docId }: { docId: string }) {
  const [chunk, setChunk] = useState(0);
  const [size, setSize] = useState(800);
  const [term, setTerm] = useState("");
  const [hits, setHits] = useState<number[]>([]);
  const [data, setData] = useState<ChunkResp | null>(null);

  const fetchChunk = useCallback(async (c: number) => {
    const url = `/docs/${encodeURIComponent(docId)}?chunk=${c}&size=${size}${term ? `&terms=${encodeURIComponent(term)}` : ""}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    const j: ChunkResp = await r.json();
    setData(j);
    setChunk(c);
  }, [docId, size, term]);

  const search = useCallback(async () => {
    if (!term) { setHits([]); await fetchChunk(0); return; }
    const r = await fetch(`/docs/search?doc=${encodeURIComponent(docId)}&term=${encodeURIComponent(term)}&size=${size}&limit=20`);
    if (!r.ok) throw new Error(await r.text());
    const j: SearchResp = await r.json();
    setHits(j.chunks);
    const first = j.chunks[0] ?? 0;
    await fetchChunk(first);
  }, [docId, size, term, fetchChunk]);

  useEffect(() => { fetchChunk(0); }, [docId]);

  const prev = () => {
    if (!hits.length) return setChunk((c) => Math.max(0, c - 1));
    const idx = hits.findIndex((h) => h >= chunk);
    const prevHit = idx <= 0 ? hits[0] : hits[idx - 1];
    fetchChunk(prevHit);
  };

  const next = () => {
    if (!hits.length) return setChunk((c) => { const n = c + 1; fetchChunk(n); return n; });
    const idx = hits.findIndex((h) => h > chunk);
    const nextHit = idx === -1 ? hits[hits.length - 1] : hits[idx];
    fetchChunk(nextHit);
  };

  const highlighted = useMemo(() => {
    if (!data) return null;
    let html = data.text;
    for (const h of data.highlights) {
      if (!h.positions?.length || !h.term) continue;
      // naive: wrap all occurrences; to avoid shifting indices, rebuild by regex
      const re = new RegExp(`(${h.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
      html = html.replace(re, '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>');
    }
    return { __html: html };
  }, [data]);

  return (
    <div className="rounded-2xl border p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Input placeholder="검색어 (terms)" value={term} onChange={(e) => setTerm(e.target.value)} className="max-w-[260px]" />
        <Button onClick={search}>Search</Button>
        <Separator orientation="vertical" className="h-6" />
        <Button variant="outline" onClick={prev}>Prev</Button>
        <Button variant="outline" onClick={next}>Next</Button>
        <div className="text-xs text-muted-foreground ml-auto">chunk {chunk} {hits.length ? `(hits: ${hits.length})` : ""}</div>
      </div>
      <Separator />
      <div className="prose prose-sm max-w-none">
        {highlighted ? (
          <div dangerouslySetInnerHTML={highlighted} />
        ) : (
          <div className="text-sm text-muted-foreground">Loading…</div>
        )}
      </div>
    </div>
  );
}
