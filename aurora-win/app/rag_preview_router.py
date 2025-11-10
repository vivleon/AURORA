"""
RAG Document Preview Router
- /docs/{doc_id} 엔드포인트를 제공하여 RAG 문서의 스니펫(snippet)을 반환합니다.
- /docs/search 엔드포인트를 제공하여 문서 내 용어(term)를 검색합니다.
- 저장소: data/rag/{doc_id}.txt (UTF-8)
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
    """보안 검사 후 로컬 파일 시스템에서 문서를 로드합니다."""
    # Directory Traversal 공격 방지
    if ".." in doc_id or "/" in doc_id or "\\" in doc_id:
        raise HTTPException(400, detail="Invalid doc_id format")
        
    p = DOC_ROOT / f"{doc_id}.txt"
    if not DOC_ROOT.exists():
        DOC_ROOT.mkdir(parents=True, exist_ok=True)
        
    if not p.exists():
        # 테스트용 임시 파일 생성
        try:
            p.write_text(f"Placeholder text for {doc_id}.\nThis is chunk 0.\nThis is chunk 1 with keyword 'test' and 'aurora'.", "utf-8")
        except IOError:
            raise HTTPException(404, detail="Document not found and placeholder could not be created")
            
    try:
        return p.read_text("utf-8", errors="ignore")
    except IOError as e:
        raise HTTPException(500, detail=f"Failed to read document: {e}")


def _slice(text: str, chunk: int, size: int) -> (int, int, str):
    """텍스트를 청크 크기(size)로 자릅니다."""
    start = max(0, chunk * size)
    end = min(len(text), start + size)
    return start, end, text[start:end]


def _highlight(s: str, terms: List[str]) -> List[Dict]:
    """텍스트(s) 내에서 용어(terms)를 찾아 위치를 반환합니다."""
    res = []
    for t in terms:
        if not t: continue
        try:
            # 대소문자 무시 (IGNORECASE)
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
    (webui_RagPreview.tsx [cite: vivleon/aurora/AURORA-main/aurora-win/aurora-win/webui/webui_RagPreview.tsx]가 호출)
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
    limit: int = Query(20, ge=1, le=50)
):
    """
    문서 내에서 특정 용어가 포함된 청크 ID 목록을 검색합니다.
    (webui_RagPreview.tsx [cite: vivleon/aurora/AURORA-main/aurora-win/aurora-win/webui/webui_RagPreview.tsx]가 호출)
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
            # 다음 위치에서 용어 검색
            idx = text_l.find(term_l, pos)
        except Exception:
            break # 검색 오류
            
        if idx < 0: 
            break # 용어 없음
            
        chunk_id = idx // size
        if chunk_id not in hits:
            hits.append(chunk_id)
            
        pos = (chunk_id + 1) * size # 다음 청크의 시작으로 이동 (중복 방지)
        if pos >= len(text_l):
            break
        
    return {"doc_id": doc, "term": term, "chunks": hits}