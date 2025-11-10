import time
from typing import Dict, Any
from app.tools import calendar, mail, browser, files, notes, screen, system, nlp

# executor.py는 'aurora-win/aurora-win/app/core/executor.py'의 것을 사용
# [cite: vivleon/aurora/AURORA-main/aurora-win/aurora-win/app/core/executor.py]

TOOL_MAP = {
    "calendar": calendar,
    "mail": mail,
    "browser": browser,
    "files": files,
    "notes": notes,
    "screen": screen,
    "system": system,
    "nlp": nlp,
}

async def run(
    plan: Dict[str, Any], 
    policy, 
    collector,  # 'audit' 대신 'collector' (EventCollector)를 받음
    db, 
    bandit,
    session_id: str = "default-session"
):
    """
    계획을 실행하고, 구형 AuditLogger 대신 EventCollector로 로그를 보냅니다.
    """
    results = []
    for step in plan.get("steps", []):
        tool = step["tool"]
        op = step["op"]
        args = step.get("args", {})
        
        mod = TOOL_MAP.get(tool)
        if not mod:
            results.append({"step": f"{tool}.{op}", "out": "Error: Tool not found", "error": "ToolNotFound"})
            continue
            
        func = getattr(mod, op, None)
        if not func:
            results.append({"step": f"{tool}.{op}", "out": "Error: Operation not found", "error": "OperationNotFound"})
            continue

        # --- 로깅 및 실행 ---
        start_time = time.monotonic()
        outcome = "success"
        err_code = None
        out = None

        try:
            # audit.record(actor="aurora", action=f"{tool}.{op}", payload=args) # [제거] 구형 해시로그 호출
            out = await func(args, policy=policy, db=db)
            
        except Exception as e:
            outcome = "error"
            err_code = type(e).__name__
            out = str(e)
        
        latency_ms = int((time.monotonic() - start_time) * 1000)

        # [추가] EventCollector (대시보드/SSE용)로 이벤트 전송
        if collector:
            event = {
                "type": "tool",
                "session_id": session_id,
                "intent": plan.get("intent", f"{tool}.{op}"),
                "tool": f"{tool}.{op}",
                "outcome": outcome,
                "latency_ms": latency_ms,
                "err_code": err_code,
                "risk": "low", # TODO: verifier에서 실제 risk 가져오기
            }
            # 비동기 큐에 이벤트 삽입 (fire-and-forget)
            try:
                await collector.enqueue(event)
            except Exception:
                # 큐가 꽉 찼거나 수집기가 중지된 경우, 로깅 실패가 실행을 막지 않도록 함
                print(f"[WARN] Failed to enqueue metric event for {tool}.{op}")

        results.append({"step": f"{tool}.{op}", "out": out, "error": err_code})
        
    return results