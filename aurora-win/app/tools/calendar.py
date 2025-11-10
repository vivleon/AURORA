# app/tools/calendar.py
import time
from app.memory.store import DB # store.py의 DB 클래스 사용

async def create(args, policy, db: DB):
    """
    일정을 'notes' 테이블에 간단한 텍스트로 저장합니다.
    (schema.sql [cite: vivleon/aurora/AURORA-main/aurora-win/schema.sql]에 'notes' 테이블이 없으므로,
     'events_raw'에 'task' 타입으로 기록하거나, 'notes' 테이블을 추가해야 합니다.)
     
    [수정]: 'notes' 테이블이 아닌 'metrics.db'의 'events_raw'에 'task'로 기록
    [대안]: app/tools/notes.py의 'save'를 호출
    """
    title = args.get("title", "Untitled Event")
    when_str = args.get("when", "now") # TODO: timeparse.py 필요
    
    print(f"[Tool.Calendar] Creating event: {title} at {when_str}")
    
    # 'notes' 테이블이 없으므로, app/tools/notes.py의 save 함수를 사용
    from . import notes
    
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