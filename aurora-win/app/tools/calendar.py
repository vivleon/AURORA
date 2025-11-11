# app/tools/calendar.py
import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

try:
    from ics import Calendar, Event
except ImportError:
    print("[WARN] 'ics' library not installed. Calendar tool will fail. (pip install ics)")
    Calendar, Event = None, None

from app.memory.store import DB

# [신규] 로컬 iCalendar 파일 경로
CALENDAR_PATH = Path(os.getenv("CALENDAR_PATH", "data/calendar/my_calendar.ics"))
CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load_calendar() -> Calendar:
    """ICS 파일을 로드하거나 새로 생성합니다."""
    if not Calendar:
        raise ImportError("'ics' library is required")
    
    if CALENDAR_PATH.exists():
        try:
            with open(CALENDAR_PATH, 'r', encoding='utf-8') as f:
                return Calendar(f.read())
        except Exception as e:
            print(f"[Tool.Calendar WARN] Failed to parse ICS file: {e}. Creating new.")
    return Calendar()

def _save_calendar(c: Calendar):
    """ICS 파일을 디스크에 저장합니다."""
    if not Calendar:
        return
    try:
        with open(CALENDAR_PATH, 'w', encoding='utf-8') as f:
            f.write(str(c))
    except IOError as e:
        print(f"[Tool.Calendar ERROR] Failed to save ICS file: {e}")

async def create(args: Dict[str, Any], policy, db: DB):
    """
    [업그레이드]
    일정을 'notes' 테이블 대신 'data/calendar/my_calendar.ics' 파일에 저장합니다.
    """
    title = args.get("title", "Untitled Event")
    when_str = args.get("when", "now")
    
    # (스텁) 'when' 파싱 로직 (timeparse.py 필요)
    # 지금은 '지금'으로 고정합니다.
    start_time = datetime.now()
    
    print(f"[Tool.Calendar] Creating ICS event: {title} at {start_time.isoformat()}")

    try:
        c = await asyncio.to_thread(_load_calendar)
        
        e = Event()
        e.name = title
        e.begin = start_time
        e.duration = timedelta(hours=args.get("duration_hours", 1))
        
        c.events.add(e)
        
        await asyncio.to_thread(_save_calendar, c)
        
        return {"created": True, "ics_path": str(CALENDAR_PATH), "title": title}
        
    except Exception as e:
        print(f"[Tool.Calendar ERROR] Failed to create ICS event: {e}")
        return {"created": False, "error": str(e)}

async def list_slots(args: Dict[str, Any], policy, db: DB):
    """
    (Auto-Scheduler)
    [업그레이드]
    'my_calendar.ics' 파일을 읽어 실제 빈 슬롯을 제안합니다.
    """
    duration_min = args.get("duration_min", 30)
    print(f"[Tool.Calendar] Finding free slots for {duration_min}min from ICS file.")

    try:
        c = await asyncio.to_thread(_load_calendar)
        
        # (스텁) 9시부터 18시까지 30분 단위로 검사
        slots = []
        check_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        for i in range(18): # 9:00 ~ 17:30 (30분 * 18)
            slot_start = check_start + timedelta(minutes=30 * i)
            slot_end = slot_start + timedelta(minutes=duration_min)
            
            is_free = True
            for e in c.events:
                # (단순 충돌 감지)
                if e.begin and e.end and (e.begin < slot_end) and (e.end > slot_start):
                    is_free = False
                    break
            
            if is_free:
                slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                })
                if len(slots) >= 5: # 최대 5개 제안
                    break
                    
            if slot_end.hour >= 18: # 18시 이후 슬롯은 중지
                break
                
        return {"slots": slots}
        
    except Exception as e:
        return {"slots": [], "error": str(e)}