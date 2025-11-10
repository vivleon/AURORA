# app/tools/calendar.py
import time
from app.memory.store import DB # store.py의 DB 클래스 사용
from . import notes # app/tools/notes.py 임포트
from typing import Dict, Any

async def create(args: Dict[str, Any], policy, db: DB):
    """
    일정 생성을 요청받아, app/tools/notes.py의 save 함수를 호출하여
    'notes' 테이블에 일정 정보를 저장합니다.
    (schema.sql에 'notes' 테이블이 정의되어 있습니다.)
    """
    title = args.get("title", "Untitled Event")
    when_str = args.get("when", "now") # TODO: timeparse.py 필요
    
    print(f"[Tool.Calendar] Creating event via notes.save: {title} at {when_str}")
    
    try:
        # notes.py의 save 함수를 직접 호출
        result = await notes.save({
            "title": f"Event: {title}",
            "body": f"Scheduled for: {when_str}",
            "pin": args.get("pin", False)
        }, policy, db)
        
        return {"created": True, "note_id": result.get("note_id"), "title": title}
        
    except Exception as e:
        print(f"[Tool.Calendar ERROR] Failed to save note: {e}")
        return {"created": False, "error": str(e)}

async def list_slots(args: Dict[str, Any], policy, db: DB):
    """
    (Auto-Scheduler 스텁)
    'notes' 테이블에서 'Event:'로 시작하는 항목을 조회하여
    "충돌"을 (시뮬레이션) 회피한 빈 슬롯을 제안합니다.
    """
    duration_min = args.get("duration_min", 30)
    print(f"[Tool.Calendar] Finding free slots for {duration_min}min (stub)")

    conn = db.connect()
    if not conn:
        return {"slots": [], "error": "DB connection failed"}
        
    try:
        cur = conn.cursor()
        # 'notes' 테이블에서 기존 일정을 (스텁) 조회
        cur.execute("SELECT title, body FROM notes WHERE title LIKE 'Event:%'")
        existing_events = cur.fetchall()
        
        print(f"[Tool.Calendar] Found {len(existing_events)} existing events (stub check).")
        
        # 실제 구현: existing_events의 'body' (예: "Scheduled for: ...")를 파싱하여
        # 요청된 duration_min과 충돌하지 않는 시간을 계산해야 합니다.
        
        # 여기서는 스텁으로 고정된 가용 슬롯을 반환합니다.
        stub_slots = [
            {"start": "2025-11-11T14:00:00", "end": "2025-11-11T15:00:00"},
            {"start": "2025-11-12T10:00:00", "end": "2025-11-12T10:30:00"},
            {"start": "2025-11-12T16:00:00", "end": "2025-11-12T18:00:00"},
        ]
        
        return {"slots": stub_slots}
        
    except Exception as e:
        return {"slots": [], "error": str(e)}
    finally:
        if conn:
            conn.close()