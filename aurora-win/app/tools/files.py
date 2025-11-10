# app/tools/files.py
# (requirements.txt에 'aiofiles' 추가 권장)
import os
from pathlib import Path

try:
    import aiofiles
except ImportError:
    print("[WARN] 'aiofiles' not installed. File tools will use sync methods. (pip install aiofiles)")
    aiofiles = None

# 보안을 위해 작업 루트를 'data/files'로 제한 (예시)
# (policy.json [cite: vivleon/aurora/AURORA-main/aurora-win/data/policy.json]의 'files.read' 스코프와 연동 필요)
FILES_ROOT = Path(os.getenv("FILES_ROOT", "data/files"))
FILES_ROOT.mkdir(parents=True, exist_ok=True)

def _secure_path(path: str) -> Path:
    """Directory Traversal 공격을 방지합니다."""
    if ".." in path or path.startswith(("/", "\\")):
        raise PermissionError("Invalid path format (absolute or traversal)")
        
    full_path = (FILES_ROOT / path).resolve()
    
    if FILES_ROOT.resolve() not in full_path.parents:
         raise PermissionError("Access Denied: Path is outside the allowed directory")
         
    return full_path

async def read(args, policy, db):
    """
    (제한된 경로에서) 비동기 파일 읽기
    """
    path_str = args.get("path")
    if not path_str:
        raise ValueError("path is required")
    
    try:
        path = _secure_path(path_str)
        print(f"[Tool.Files] Reading from: {path}")
        
        if aiofiles:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
        else: # 폴백
            content = path.read_text('utf-8')
            
        return {"content": content}
    except Exception as e:
        return {"content": None, "error": str(e)}

async def write(args, policy, db):
    """
    (제한된 경로에) 비동기 파일 쓰기
    """
    path_str = args.get("path")
    content = args.get("content", "")
    if not path_str:
        raise ValueError("path is required")
        
    try:
        path = _secure_path(path_str)
        print(f"[Tool.Files] Writing {len(content)} chars to: {path}")
        
        if aiofiles:
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(content)
        else: # 폴백
            path.write_text(content, 'utf-8')
            
        return {"written": True, "path": str(path)}
    except Exception as e:
        return {"written": False, "error": str(e)}

async def delete(args, policy, db):
    """
    ! HIGH-RISK !
    (제한된 경로에서) 파일 삭제
    """
    path_str = args.get("path")
    if not path_str:
        raise ValueError("path is required")
        
    try:
        path = _secure_path(path_str)
        print(f"[Tool.Files] Deleting: {path}")
        
        os.remove(path) # 동기 삭제 (위험하므로 신중)
        
        return {"deleted": True, "path": str(path)}
    except Exception as e:
        return {"deleted": False, "error": str(e)}