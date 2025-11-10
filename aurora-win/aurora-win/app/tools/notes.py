async def save(args, policy, db):
    # TODO: SQLite DB 'notes' 테이블에 저장
    return {"saved": True, "title": args.get("title")}

async def pin(args, policy, db):
    # TODO: 'notes' 테이블 pin 플래그 업데이트
    return {"pinned": True, "note_id": args.get("note_id")}