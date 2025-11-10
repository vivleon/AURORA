# app/memory/vectorstore.py (수정)
# FAISS 인덱스 로드/저장, 추가(add), 검색(search) 기능 완성

import os
from pathlib import Path
import numpy as np

try:
    import faiss
except ImportError:
    print("[WARN] 'faiss-cpu' not installed. Vectorstore (RAG) will not work. (pip install faiss-cpu)")
    faiss = None

# TODO: 임베딩 모델 로직을 model_runner.py로 이동/통합해야 함
# 임시로 스텁 함수 생성
async def get_embedding(text: str) -> np.ndarray:
    # 실제로는 app/router/model_runner.py의
    # "local://onnx/e5-small" 모델을 호출해야 함
    dim = 384 # e5-small-v2
    print(f"[Vectorstore] Stub embedding generated for: {text[:20]}...")
    return np.random.rand(1, dim).astype('float32')

class VectorStore:
    def __init__(self, index_path: str = "data/embeddings/aurora.index", dim: int = 384):
        if not faiss:
            raise ImportError("FAISS is not installed.")
            
        self.index_path = Path(index_path)
        self.dim = dim
        self.index = self._load_index()
        # FAISS 인덱스는 ID 매핑을 별도로 관리해야 함
        self.doc_id_map: Dict[int, str] = {} # FAISS index ID -> "doc_id:chunk_idx"
        self._load_map()

    def _ensure_dir(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_index(self):
        self._ensure_dir()
        if self.index_path.exists():
            try:
                print(f"[Vectorstore] Loading index from {self.index_path}")
                return faiss.read_index(str(self.index_path))
            except Exception as e:
                print(f"[Vectorstore ERROR] Failed to load index: {e}. Creating new one.")
        
        print("[Vectorstore] Initializing new FAISS IndexFlatL2")
        return faiss.IndexFlatL2(self.dim)
    
    def _map_path(self) -> Path:
        return self.index_path.with_suffix(".map.json")

    def _load_map(self):
        map_path = self._map_path()
        if map_path.exists():
            try:
                import json
                map_data = json.loads(map_path.read_text('utf-8'))
                # JSON 키는 문자열이므로 다시 int로 변환
                self.doc_id_map = {int(k): v for k, v in map_data.items()}
                print(f"[Vectorstore] Loaded {len(self.doc_id_map)} ID mappings.")
            except Exception as e:
                print(f"[Vectorstore ERROR] Failed to load ID map: {e}")

    def save_index(self):
        self._ensure_dir()
        try:
            print(f"[Vectorstore] Saving index to {self.index_path}")
            faiss.write_index(self.index, str(self.index_path))
            
            import json
            map_path = self._map_path()
            map_path.write_text(json.dumps(self.doc_id_map), 'utf-8')
            print(f"[Vectorstore] Saved {len(self.doc_id_map)} ID mappings.")
        except Exception as e:
            print(f"[Vectorstore ERROR] Failed to save index or map: {e}")

    async def add(self, doc_id: str, chunks: List[str]):
        """
        문서 청크를 임베딩하고 인덱스에 추가합니다.
        """
        if not chunks:
            return
            
        print(f"[Vectorstore] Adding {len(chunks)} chunks for doc: {doc_id}")
        
        # 1. 청크 임베딩 (배치 처리가 더 효율적)
        vectors = []
        for chunk_text in chunks:
            vec = await get_embedding(chunk_text)
            vectors.append(vec)
        
        if not vectors:
            return
            
        batch_vectors = np.concatenate(vectors, axis=0).astype('float32')
        
        # 2. FAISS ID 매핑
        start_id = self.index.ntotal
        faiss_ids = list(range(start_id, start_id + len(chunks)))
        
        for i, chunk_idx in enumerate(chunks):
            faiss_id = faiss_ids[i]
            map_key = f"{doc_id}:{i}" # 예: "my_doc:0", "my_doc:1"
            self.doc_id_map[faiss_id] = map_key
            
        # 3. 인덱스에 추가
        self.index.add(batch_vectors)
        print(f"[Vectorstore] Index ntotal: {self.index.ntotal}")

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        쿼리를 임베딩하고 인덱스에서 K개의 유사한 청크를 검색합니다.
        """
        if not self.index.ntotal:
            return [] # 인덱스가 비어있음
            
        # 1. 쿼리 임베딩
        query_vector = await get_embedding(query)
        
        # 2. FAISS 검색
        # D = distances, I = indices
        distances, indices = self.index.search(query_vector, k)
        
        results = []
        for i in range(k):
            faiss_id = int(indices[0][i])
            if faiss_id < 0:
                continue # 유효하지 않은 인덱스
                
            map_key = self.doc_id_map.get(faiss_id)
            if not map_key:
                print(f"[Vectorstore WARN] No ID mapping found for FAISS ID: {faiss_id}")
                continue
                
            doc_id, chunk_idx_str = map_key.split(":", 1)
            
            results.append({
                "doc_id": doc_id,
                "chunk_idx": int(chunk_idx_str),
                "score": float(distances[0][i])
            })
            
        return results

# --- 싱글톤 인스턴스 ---
# (RAG 프리뷰 라우터 등에서 이 인스턴스를 공유하여 사용)
_vectorstore_instance = VectorStore()