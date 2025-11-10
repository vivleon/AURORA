import time
import asyncio 
from typing import Dict, Any
# [신규] rag 도구 임포트
from app.tools import calendar, mail, browser, files, notes, screen, system, nlp, rag

TOOL_MAP = {
    "calendar": calendar,
    "mail": mail,
    "browser": browser,
    "files": files,
    "notes": notes,
    "screen": screen,
    "system": system,
    "nlp": nlp,
    "rag": rag, # [신규] RAG 도구 등록
}

async def run(
    plan: Dict[str, Any], 
    policy, 
    collector,
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
    
    context_key = plan.get("intent", "global")
    
    for step in plan.get("steps", []):
        tool = step["tool"]
        op = step["op"]
        args = step.get("args", {})
        tool_op_key = f"{tool}.{op}" # 예: "rag.search"
        
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

        # 1. EventCollector (대시보드/SSE용)로 이벤트 전송
        if collector:
            # [신규] RAG 도구 실행 시 'type'을 'rag'로 설정
            event_type = "rag" if tool == "rag" else "tool"
            
            event = {
                "type": event_type,
                "session_id": session_id,
                "intent": context_key,
                "tool": tool_op_key,
                "outcome": outcome,
                "latency_ms": latency_ms,
                "err_code": err_code,
                "risk": "low",
                # [신규] RAG 결과(evidence) 수량 로깅 (대시보드 품질 측정용)
                "evidences": len(out.get("results", [])) if tool == "rag" and out else 0
            }
            try:
                await collector.enqueue(event)
            except Exception:
                print(f"[WARN] Failed to enqueue metric event for {tool_op_key}")

        # 2. 자가학습: 보상 신호 계산 및 Bandit 업데이트
        if outcome == "success":
            reward = 1.0 - (latency_ms / 10000.0)
        else:
            reward = -0.5
        
        if bandit:
            try:
                await asyncio.to_thread(
                    bandit.update, 
                    context_key,
                    tool_op_key,
                    reward
                )
                print(f"[Bandit] Updated '{context_key}' -> '{tool_op_key}' with reward: {reward:.2f}")
            except Exception as e:
                print(f"[WARN] Failed to update bandit state: {e}")

        results.append({"step": tool_op_key, "out": out, "error": err_code})
        
    return results