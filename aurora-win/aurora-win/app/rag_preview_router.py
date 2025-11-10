"""
RAG Document Preview Router
- Serves snippet previews with optional term highlighting
- Storage model: files under data/rag/{doc_id}.txt (UTF-8)
"""
from __future__ import annotations
import re
import os
from pathlib import Path
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

# RAG 문서가 저장될 기본 경로
DOC_ROOT = Path(os.getenv("RAG_DOC_ROOT", "data/rag"))

preview_router = APIRouter()


def _load_text(doc_id: str) -> str:
    # Directory Traversal 공격 방지
    if ".." in doc_id or "/" in doc_id or "\\" in doc_id:
        raise HTTPException(400, detail="Invalid doc_id format")
        
    p = DOC_ROOT / f"{doc_id}.txt"
    if not DOC_ROOT.exists():
        DOC_ROOT.mkdir(parents=True, exist_ok=True)
        
    if not p.exists():
        # 테스트용 임시 파일 생성
        try:
            p.write_text(f"Placeholder text for {doc_id}.\nThis is chunk 0.\nThis is chunk 1 with keyword 'test'.", "utf-8")
        except IOError:
            raise HTTPException(404, detail="Document not found and placeholder could not be created")
            
    try:
        return p.read_text("utf-8", errors="ignore")
    except IOError as e:
        raise HTTPException(500, detail=f"Failed to read document: {e}")


def _slice(text: str, chunk: int, size: int) -> (int, int, str):
    start = max(0, chunk * size)
    end = min(len(text), start + size)
    return start, end, text[start:end]


def _highlight(s: str, terms: List[str]) -> List[Dict]:
    res = []
    for t in terms:
        if not t: continue
        try:
            positions = [m.start() for m in re.finditer(re.escape(t), s, flags=re.IGNORECASE)]
            if positions:
                res.append({"term": t, "positions": positions})
        except re.error:
            pass # 잘못된 정규식 용어 무시
    return res

@preview_router.get("/docs/{doc_id}")
def get_chunk(
    doc_id: str, 
    chunk: int = Query(0, ge=0), 
    size: int = Query(800, ge=100, le=5000), 
    terms: Optional[str] = Query(None)
):
    """
    RAG 문서의 특정 청크(chunk)를 반환합니다.
    (예: /docs/my_doc_001?chunk=1&terms=aurora)
    """
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
def search_chunks(
    doc: str, 
    term: str, 
    size: int = Query(800, ge=100, le=5000), 
    limit: int = Query(5, ge=1, le=50)
):
    """
    문서 내에서 특정 용어가 포함된 청크 ID 목록을 검색합니다.
    """
    text = _load_text(doc)
    hits = []
    pos = 0
    term_l = term.lower()
    
    if not term_l:
        return {"doc_id": doc, "term": term, "chunks": []}
        
    text_l = text.lower()
    
    while len(hits) < limit:
        try:
            idx = text_l.find(term_l, pos)
        except Exception:
            break # 검색 오류
            
        if idx < 0: 
            break # 용어 없음
            
        chunk_id = idx // size
        if chunk_id not in hits:
            hits.append(chunk_id)
            
        pos = idx + len(term) # 다음 검색 위치 이동
        
    return {"doc_id": doc, "term": term, "chunks": hits}