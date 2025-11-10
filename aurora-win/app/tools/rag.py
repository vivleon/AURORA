# app/tools/rag.py
from typing import Dict, Any
from app.memory.vectorstore import get_vectorstore
from app.memory.store import DB

async def search(args: Dict[str, Any], policy, db: DB):
    """
    사용자의 쿼리를 받아 Vectorstore(FAISS)에서
    유사도 검색(RAG)을 수행합니다.
    """
    query = args.get("query")
    k = args.get("k", 3) # 상위 3개 검색
    
    if not query:
        raise ValueError("RAG search 'query' is required")

    print(f"[Tool.RAG] Searching vectorstore for: '{query[:30]}...' (k={k})")
    
    try:
        vstore = get_vectorstore()
        
        # vectorstore.py의 search 함수 호출
        # (get_embedding -> model_runner.py 호출 포함)
        search_results = await vstore.search(query=query, k=k)
        
        # [신규] 검색 결과를 대시보드(RAG 패널)가 수집할 수 있도록
        # 'rag' 타입 이벤트를 EventCollector에 전달해야 하지만,
        # executor.py에서만 collector에 접근 가능하므로 여기서는 결과만 반환합니다.
        
        # (참고: RAG 패널은 'rag_hits' 테이블을 읽으므로,
        # 향후 executor에서 이 결과를 받아 'rag_hits'에 저장해야 함)

        return {
            "query": query,
            "results": search_results,
            "summary": f"Found {len(search_results)} RAG results."
        }
        
    except Exception as e:
        print(f"[Tool.RAG ERROR] RAG search failed: {e}")
        return {"query": query, "results": [], "error": str(e)}