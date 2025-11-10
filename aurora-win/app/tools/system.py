# app/tools/system.py
# (planner_consent_gate [cite: vivleon/aurora/AURORA-main/aurora-win/app/core/planner_consent_gate.py]에서 'system.exec'는 고위험)

import asyncio
import os
from pathlib import Path

# (policy.json [cite: vivleon/aurora/AURORA-main/aurora-win/data/policy.json]의 'system.exec.limited' 스코프)
SIGNED_SCRIPT_PATH = Path(os.getenv("SIGNED_SCRIPT_PATH", "scripts/signed_ps"))
SIGNED_SCRIPT_PATH.mkdir(parents=True, exist_ok=True)

async def _run_async_subprocess(command_list: list[str]):
    """비동기 서브프로세스 래퍼"""
    process = await asyncio.create_subprocess_exec(
        *command_list,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    stdout_str = stdout.decode('utf-8', errors='ignore').strip()
    stderr_str = stderr.decode('utf-8', errors='ignore').strip()
    
    if process.returncode != 0:
        raise RuntimeError(f"Command failed (Code {process.returncode}): {stderr_str}")
        
    return stdout_str

async def exec(args, policy, db):
    """
    ! HIGH-RISK !
    일반 시스템 명령을 비동기로 실행합니다. (예: ['ping', '8.8.8.8'])
    """
    command_list = args.get("command") # ['ping', '8.8.8.8']
    if not command_list or not isinstance(command_list, list):
        raise ValueError("command (as a list) is required for exec")
        
    print(f"[Tool.System] Executing command: {command_list}")
    
    try:
        stdout = await _run_async_subprocess(command_list)
        return {"return_code": 0, "stdout": stdout}
    except Exception as e:
        return {"return_code": -1, "stdout": None, "error": str(e)}

async def exec_limited(args, policy, db):
    """
    ! HIGH-RISK !
    'scripts/signed_ps/' 디렉터리 내의 서명된 스크립트만 실행합니다.
    """
    script_name = args.get("script_name")
    if not script_name:
        raise ValueError("script_name is required for exec_limited")

    # 보안 경로 검증 (Directory Traversal 방지)
    try:
        script_path = (SIGNED_SCRIPT_PATH / script_name).resolve()
        if SIGNED_SCRIPT_PATH.resolve() not in script_path.parents:
             raise PermissionError("Access Denied: Path is outside the allowed directory")
    except Exception as e:
        return {"return_code": -1, "error": str(e)}

    if not script_path.exists():
        return {"return_code": -1, "error": f"Script not found: {script_name}"}

    # TODO: PowerShell 스크립트 서명 검증 로직 (필수)
    # (예: Get-AuthenticodeSignature)
    print(f"[Tool.System] Verifying signature for: {script_path} (Not Implemented)")
    
    
    command = ['powershell', '-File', str(script_path)]
    print(f"[Tool.System] Executing limited script: {command}")
    
    try:
        stdout = await _run_async_subprocess(command)
        return {"return_code": 0, "stdout": stdout}
    except Exception as e:
        return {"return_code": -1, "stdout": None, "error": str(e)}