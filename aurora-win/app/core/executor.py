import time
import asyncio # [신규] 비동기 스레드 실행을 위해 임포트
from typing import Dict, Any
from app.tools import calendar, mail, browser, files, notes, screen, system, nlp

# executor.py는 'aurora-win/aurora-win/app/core/executor.py'의 것을 사용
#

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
    [업그레이드]
    계획을 실행하고, EventCollector로 로그를 보내며,
    실행 결과를 '보상(reward)'으로 변환하여 'Contextual Bandit'의
    update 함수를 호출함으로써 자가학습을 활성화합니다.
    """
    results = []
    
    # [신규] 이 계획의 컨텍스트 키 (예: "intent:schedule_find")
    # Bandit은 이 컨텍스트를 기반으로 학습합니다.
    context_key = plan.get("intent", "global")
    
    for step in plan.get("steps", []):
        tool = step["tool"]
        op = step["op"]
        args = step.get("args", {})
        tool_op_key = f"{tool}.{op}" # 예: "calendar.list_slots"
        
        mod = TOOL_MAP.get(tool)
        if not mod:
            results.append({"step": tool_op_key, "out": "Error: Tool not found", "error": "ToolNotFound"})
            continue
            
        func = getattr(mod, op, None)
        if not func:
            results.append({"step": tool_op_key, "out": "Error: Operation not found", "error": "OperationNotFound"})
            continue

        # --- 로깅 및 실행 ---
        start_time = time.monotonic()
        outcome = "success"
        err_code = None
        out = None

        try:
            out = await func(args, policy=policy, db=db)
            
        except Exception as e:
            outcome = "error"
            err_code = type(e).__name__
            out = str(e)
        
        latency_ms = int((time.monotonic() - start_time) * 1000)

        # 1. [기존] EventCollector (대시보드/SSE용)로 이벤트 전송
        if collector:
            event = {
                "type": "tool",
                "session_id": session_id,
                "intent": context_key, # 컨텍스트 키 사용
                "tool": tool_op_key,
                "outcome": outcome,
                "latency_ms": latency_ms,
                "err_code": err_code,
                "risk": "low", # TODO: verifier에서 실제 risk 가져오기
            }
            try:
                await collector.enqueue(event)
            except Exception:
                print(f"[WARN] Failed to enqueue metric event for {tool_op_key}")

        # 2. [신규] 자가학습: 보상 신호 계산 및 Bandit 업데이트
        # (docs/aurora_self_learning_module.md 기반 보상 함수)
        if outcome == "success":
            # 성공 시 1.0에서 시작, 1초당 0.1씩 감소
            reward = 1.0 - (latency_ms / 10000.0)
        else:
            # 오류 시 -0.5
            reward = -0.5
        
        # bandit.update는 보상 범위를 [-1.0 ~ 1.5]로 가정함
        
        if bandit:
            try:
                # bandit.update는 동기 (파일 I/O)이므로 스레드에서 실행
                await asyncio.to_thread(
                    bandit.update, 
                    context_key, # 컨텍스트 (예: "일정 추천")
                    tool_op_key,   # 도구 (예: "calendar.list_slots")
                    reward         # 보상 (예: 0.85)
                )
                print(f"[Bandit] Updated '{context_key}' -> '{tool_op_key}' with reward: {reward:.2f}")
            except Exception as e:
                print(f"[WARN] Failed to update bandit state: {e}")

        results.append({"step": tool_op_key, "out": out, "error": err_code})
        
    return results
