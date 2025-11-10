async def compose(args, policy, db):
# TODO: SMTP 초안 저장(로컬 큐)
return {"draft": True, "subject": args.get("subject")}