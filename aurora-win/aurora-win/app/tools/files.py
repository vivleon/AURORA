# app/tools/files.py
# 'files.delete'는 verifier.py와 planner_consent_gate.py에 의해
# 'high' 리스크로 간주됩니다.

async def read(args, policy, db):
    """
    파일 읽기 (향후 policy.allowed(f"files.read.{path}") 검사 필요)
    """
    path = args.get("path", "unknown_file.txt")
    print(f"[Tool] Reading file: {path}")
    # TODO: 실제 파일 읽기 로직
    # with open(path, 'r', encoding='utf-8') as f:
    #     content = f.read()
    return {"content": f"file content placeholder for {path}"}

async def delete(args, policy, db):
    """
    ! HIGH-RISK !
    파일 삭제
    """
    path = args.get("path")
    if not path:
        raise ValueError("Path is required for delete operation")
        
    print(f"[Tool] Deleting file: {path}")
    # TODO: 실제 파일 삭제 로직
    # import os
    # os.remove(path)
    return {"deleted": True, "path": path}

async def write(args, policy, db):
    """
    파일 쓰기
    """
    path = args.get("path", "output.txt")
    content = args.get("content", "")
    print(f"[Tool] Writing to file: {path}")
    # TODO: 실제 파일 쓰기 로직
    # with open(path, 'w', encoding='utf-8') as f:
    #     f.write(content)
    return {"written": True, "path": path}