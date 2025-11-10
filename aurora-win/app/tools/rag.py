# app/tools/rag.py
import asyncio # [신규] 백그라운드 작업을 위해 임포트
import time    # [신규] 타임스탬프용
from typing import Dict, Any, List
from app.memory.vectorstore import get_vectorstore
from app.memory.store import DB

async def _log_hits_background(db: DB, results: List[Dict[str, Any]]):
    """
    [신규] RAG 검색 결과를 백그라운드에서 'rag_hits' 테이블에 기록합니다.
    (대시보드 패널 데이터 소스)
    """
    if not results:
        return

    now = time.time()
    hits_data = []
    for r in results:
        hits_data.append(
            (now, r.get("doc_id"), r.get("chunk_idx"))
        )

    conn = db.connect()
    if not conn:
        print("[Tool.RAG ERROR] Failed to connect to DB for logging hits.")
        return
        
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO rag_hits (ts, doc, chunk_idx) VALUES (?, ?, ?)",
            hits_data
        )
        conn.commit()
        print(f"[Tool.RAG] Logged {len(hits_data)} hits to 'rag_hits' table.")
    except Exception as e:
        # 백그라운드 작업이므로 메인 스레드에 영향을 주지 않음
        print(f"[Tool.RAG ERROR] Failed to log hits to DB: {e}")
    finally:
        if conn:
            conn.close()

async def search(args: Dict[str, Any], policy, db: DB):
    """
    [업그레이드]
    사용자의 쿼리로 RAG 검색을 수행하고,
    성공 시 _log_hits_background를 호출하여 대시보드용 로그를 저장합니다.
    """
    query = args.get("query")
    k = args.get("k", 3) # 상위 3개 검색
    
    if not query:
        raise ValueError("RAG search 'query' is required")

    print(f"[Tool.RAG] Searching vectorstore for: '{query[:30]}...' (k={k})")
    
    try:
        vstore = get_vectorstore()
        
        # vectorstore.py의 search 함수 호출
        search_results = await vstore.search(query=query, k=k)
        
        # [신규] 대시보드 로깅 (Fire-and-Forget)
        if search_results:
            asyncio.create_task(_log_hits_background(db, search_results))

        return {
            "query": query,
            "results": search_results,
            "summary": f"Found {len(search_results)} RAG results."
        }
        
    except Exception as e:
        print(f"[Tool.RAG ERROR] RAG search failed: {e}")
        return {"query": query, "results": [], "error": str(e)}
