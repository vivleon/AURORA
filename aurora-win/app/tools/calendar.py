# app/tools/calendar.py
import time
from app/memory.store import DB # store.py의 DB 클래스 사용
from . import notes # app/tools/notes.py 임포트

async def create(args, policy, db: DB):
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