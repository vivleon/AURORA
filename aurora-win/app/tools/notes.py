# app/tools/notes.py
# [UPDATE]: 'schema.sql'에 'notes' 테이블이 추가됨에 따라
# 'events_raw' 대신 실제 'notes' 테이블을 사용하도록 수정합니다.
import time
from app.memory.store import DB

async def save(args, policy, db: DB):
    """
    노트를 'notes' 테이블에 저장합니다.
    (app/tools/calendar.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/tools/calendar.py]가 이 함수를 호출합니다)
    """
    title = args.get("title", "Untitled")
    body = args.get("body", "")
    pin = args.get("pin", False)
    now = time.time()
    
    print(f"[Tool.Notes] Saving note to 'notes' table: {title}")
    
    conn = db.connect()
    if not conn:
        return {"saved": False, "error": "DB connection failed"}
        
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
        return {"saved": True, "note_id": note_id, "title": title, "pin": pin}
    except Exception as e:
        return {"saved": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

async def get(args, policy, db: DB):
    """
    'notes' 테이블에서 노트를 ID로 조회합니다.
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
    'notes' 테이블의 노트를 고정(pin)합니다.
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