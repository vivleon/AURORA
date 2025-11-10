# app/tools/system.py
# 'system.exec'와 'system.exec.limited'는 'high' 리스크 작업입니다.

import subprocess
import os

SIGNED_SCRIPT_PATH = "scripts/signed_ps/"

async def exec(args, policy, db):
    """
    ! HIGH-RISK !
    일반 시스템 명령을 실행합니다.
    """
    command = args.get("command")
    if not command:
        raise ValueError("command is required for exec")
        
    # 예: ['powershell', '-Command', 'Get-Process']
    # 보안상 매우 위험하므로, 실제 운영 시에는 엄격한 필터링 필요
    print(f"[Tool] Executing command: {command}")
    
    # TODO: 실제 subprocess 실행 로직
    # try:
    #     result = subprocess.run(command, capture_output=True, text=True, check=True, shell=False)
    #     return {"return_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    # except Exception as e:
    #     return {"return_code": -1, "error": str(e)}

    return {"return_code": 0, "stdout": f"placeholder output for '{command}'"}

async def exec_limited(args, policy, db):
    """
    ! HIGH-RISK !
    'scripts/signed_ps/' 디렉터리 내의 서명된 스크립트만 실행합니다.
    (index.html, sec 6. 'system.exec.limited' 정책)
    """
    script_name = args.get("script_name")
    if not script_name:
        raise ValueError("script_name is required for exec_limited")

    # 보안 경로 검증 (Directory Traversal 방지)
    base_path = os.path.abspath(SIGNED_SCRIPT_PATH)
    script_path = os.path.abspath(os.path.join(base_path, script_name))

    if os.path.commonpath([base_path]) != os.path.commonpath([base_path, script_path]):
        return {"return_code": -1, "error": "Access Denied: Path is outside the allowed directory"}

    if not os.path.exists(script_path):
        return {"return_code": -1, "error": f"Script not found: {script_name}"}

    # TODO: PowerShell 스크립트 서명 검증 로직 추가 (필수)
    # (예: Get-AuthenticodeSignature)
    
    command = ['powershell', '-File', script_path]
    print(f"[Tool] Executing limited script: {command}")

    # TODO: 실제 subprocess 실행 로직
    
    return {"return_code": 0, "stdout": f"placeholder output for limited script '{script_name}'"}