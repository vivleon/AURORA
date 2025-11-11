# app/tools/notes.py
# [UPDATE]: 'schema.sql'에 'notes' 테이블이 추가됨에 따라
# 'events_raw' 대신 실제 'notes' 테이블을 사용하도록 수정합니다.
import time
import asyncio # [신규] 백그라운드 작업을 위해 임포트
from app.memory.store import DB
from app.memory.vectorstore import get_vectorstore # [신규] RAG 벡터저장소 임포트

async def _ingest_to_vectorstore(doc_id: str, body: str):
    """
    [신규] RAG 인제스트를 위한 백그라운드 작업
    노트 본문을 청크(여기서는 단일 청크)로 나누고 벡터 저장소에 추가합니다.
    (vectorstore.py의 add -> get_embedding -> model_runner.py 호출)
    """
    if not body or len(body.strip()) < 20: # 너무 짧은 텍스트는 RAG 인덱싱 무시
        print(f"[RAG] Ingest skipped for {doc_id} (too short)")
        return
        
    try:
        vstore = get_vectorstore()
        
        # 간단히 본문 전체를 단일 청크(chunk)로 사용
        chunks = [body] 
        
        # doc_id 예시: "note:123" (DB의 note.id 사용)
        await vstore.add(doc_id=doc_id, chunks=chunks)
        
        # (중요) FAISS 인덱스를 디스크에 즉시 저장
        # (프로덕션에서는 주기적으로 저장하는 것이 효율적)
        await asyncio.to_thread(vstore.save_index) 
        
        print(f"[RAG] Successfully ingested {doc_id} into vectorstore.")
    except Exception as e:
        # 이 오류가 메인 API 응답을 막지 않도록 함
        print(f"[RAG ERROR] Background ingestion failed for {doc_id}: {e}")

async def save(args, policy, db: DB):
    """
    [업그레이드]
    노트를 'notes' 테이블에 저장하고,
    성공 시 _ingest_to_vectorstore 백그라운드 작업을 트리거합니다.
    """
    title = args.get("title", "Untitled")
    body = args.get("body", "")
    pin = args.get("pin", False)
    now = time.time()
    
    print(f"[Tool.Notes] Saving note to 'notes' table: {title}")
    
    conn = db.connect()
    if not conn:
        return {"saved": False, "error": "DB connection failed"}
        
    note_id = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO notes (title, body, pin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, body, 1 if pin else 0, now, now)
        )
        note_id = cur.lastrowid
        conn.commit()
        
        # [신규] RAG 인제스트 (Fire-and-Forget)
        # 노트 저장이 성공하면, API 응답을 기다리게 하지 않고
        # 백그라운드에서 벡터화를 수행합니다.
        if note_id and body:
            doc_id = f"note:{note_id}"
            asyncio.create_task(_ingest_to_vectorstore(doc_id, body))
            
        return {"saved": True, "note_id": note_id, "title": title, "pin": pin}
        
    except Exception as e:
        return {"saved": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

async def get(args, policy, db: DB):
    """
    'notes' 테이블에서 노트를 ID로 조회합니다. (변경 없음)
    """
    note_id = args.get("note_id")
    if not note_id:
        raise ValueError("note_id is required")
        
    print(f"[Tool.Notes] Getting note from 'notes' table: {note_id}")
    
    conn = db.connect()
    if not conn:
        return {"note": None, "error": "DB connection failed"}
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title, body, pin, created_at FROM notes WHERE id=?", (note_id,))
        row = cur.fetchone()
        if not row:
            return {"note": None, "error": "Note not found"}
            
        return {
            "note_id": row["id"], 
            "title": row["title"], 
            "body": row["body"],
            "pin": bool(row["pin"]),
            "created_at": row["created_at"]
        }
    except Exception as e:
        return {"note": None, "error": str(e)}
    finally:
        if conn:
            conn.close()

async def pin(args, policy, db: DB):
    """
    'notes' 테이블의 노트를 고정(pin)합니다. (변경 없음)
    """
    note_id = args.get("note_id")
    pin_status = args.get("pin", True) # True/False로 고정/해제
    if not note_id:
        raise ValueError("note_id is required to pin/unpin")
        
    print(f"[Tool.Notes] Setting pin={pin_status} for note: {note_id}")
    
    conn = db.connect()
    if not conn:
        return {"pinned": False, "error": "DB connection failed"}

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE notes SET pin = ?, updated_at = ? WHERE id = ?",
            (1 if pin_status else 0, time.time(), note_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            return {"pinned": False, "note_id": note_id, "error": "Note not found"}
            
        return {"pinned": pin_status, "note_id": note_id}
    except Exception as e:
        return {"pinned": False, "error": str(e)}
    finally:
        if conn:
            conn.close()