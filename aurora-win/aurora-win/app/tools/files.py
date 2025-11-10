async def read(args, policy, db):
    # TODO: 파일 읽기 (policy.allowed(f"files.read.{path}") 확인 필요)
    return {"content": "file content placeholder"}

async def delete(args, policy, db):
    # ! HIGH-RISK !
    # TODO: 파일 삭제 로직
    return {"deleted": True, "path": args.get("path")}