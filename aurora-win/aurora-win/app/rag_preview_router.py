"""
RAG Document Preview Router
- Serves snippet previews with optional term highlighting
- Storage model: files under data/rag/{doc_id}.txt (UTF-8)
- Chunking: fixed-size windows (default 800 chars) addressed by chunk index

Endpoints:
  GET /docs/{doc_id}
    ?chunk=12&size=800&terms=alpha,beta
    -> { doc_id, chunk, start, end, text, highlights: [{term, positions: [start..]}] }

  GET /docs/search
    ?doc=doc_id&term=keyword&limit=5
    -> returns first N matching chunk indices
"""
from __future__ import annotations
import re, json
from pathlib import Path
from typing import List, Dict

from fastapi import APIRouter, HTTPException, Query

DOC_ROOT = Path("data/rag")
preview_router = APIRouter()


def _load_text(doc_id: str) -> str:
    p = DOC_ROOT / f"{doc_id}.txt"
    if not p.exists():
        raise HTTPException(404, detail="document not found")
    return p.read_text("utf-8", errors="ignore")


def _slice(text: str, chunk: int, size: int) -> (int, int, str):
    start = max(0, chunk * size)
    end = min(len(text), start + size)
    return start, end, text[start:end]


def _highlight(s: str, terms: List[str]) -> List[Dict]:
    res = []
    for t in terms:
        if not t: continue
        positions = [m.start() for m in re.finditer(re.escape(t), s, flags=re.IGNORECASE)]
        res.append({"term": t, "positions": positions})
    return res

@preview_router.get("/docs/{doc_id}")
def get_chunk(doc_id: str, chunk: int = 0, size: int = 800, terms: str | None = Query(None)):
    text = _load_text(doc_id)
    start, end, snip = _slice(text, chunk, size)
    hl = _highlight(snip, terms.split(",")) if terms else []
    return {
        "doc_id": doc_id,
        "chunk": chunk,
        "start": start,
        "end": end,
        "text": snip,
        "highlights": hl,
    }

@preview_router.get("/docs/search")
def search(doc: str, term: str, size: int = 800, limit: int = 5):
    text = _load_text(doc)
    hits = []
    pos = 0
    term_l = term.lower()
    while len(hits) < limit:
        idx = text.lower().find(term_l, pos)
        if idx < 0: break
        chunk = idx // size
        if chunk not in hits:
            hits.append(chunk)
        pos = idx + 1
    return {"doc_id": doc, "term": term, "chunks": hits[:limit]}
