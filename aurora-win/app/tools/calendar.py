async def create(args, policy, db):
# TODO: ics 파일/SQLite 저장
return {"created": True, "title": args.get("title")}