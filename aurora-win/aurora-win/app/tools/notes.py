# app/tools/notes.py
# index.html (sec 1.6, 3.3)에 정의된 기능

async def save(args, policy, db):
    """
    노트를 DB에 저장합니다. (app/memory/store.py의 DB 스텁 사용)
    """
    title = args.get("title", "Untitled")
    body = args.get("body", "")
    pin = args.get("pin", False)
    
    print(f"[Tool] Saving note: {title}")
    
    # TODO: db(store.py)에 실제 DB 저장 로직 구현
    # conn = db.connect()
    # if conn:
    #     conn.execute(
    #         "INSERT INTO notes (title, body, pin, created_at) VALUES (?, ?, ?, ?)",
    #         (title, body, 1 if pin else 0, time.time())
    #     )
    #     conn.commit()
    #     conn.close()
    
    return {"saved": True, "title": title, "pin": pin}

async def pin(args, policy, db):
    """
    노트를 고정(pin)합니다.
    """
    note_id = args.get("note_id")
    if not note_id:
        raise ValueError("note_id is required to pin")
        
    print(f"[Tool] Pinning note: {note_id}")
    # TODO: DB 업데이트 로직
    return {"pinned": True, "note_id": note_id}

async def get(args, policy, db):
    """
    노트를 조회합니다.
    """
    note_id = args.get("note_id")
    print(f"[Tool] Getting note: {note_id}")
    # TODO: DB 조회 로직
    return {"note_id": note_id, "title": "Placeholder Title", "body": "Placeholder body"}