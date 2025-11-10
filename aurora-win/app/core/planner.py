# app/core/planner.py
from typing import Dict, Any

# [신규] nlp.py의 classify 함수를 호출하기 위해 model_runner 임포트
# (nlp.py는 model_runner를 사용합니다)
from app.router import model_runner
from app.tools import nlp

async def make_plan(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    [업그레이드]
    1. LLM(model_runner)을 호출하여 사용자의 '의도(intent)'를 분류합니다.
    2. 분류된 의도에 따라 적절한 도구(tool)와 작업(op)을 매핑합니다.
    3. LLM이 실패할 경우 기존의 키워드 기반으로 폴백(fallback)합니다.
    """
    
    intent = "unknown"
    
    # 1. LLM 기반 의도 분류 시도
    if model_runner:
        try:
            # nlp.classify는 내부적으로 model_runner(task="intent")를 호출합니다.
            categories = ["schedule", "mail_send", "mail_compose", "search", "ocr", "summarize", "notes"]
            result = await nlp.classify({"text": user_input, "categories": categories}, policy=None, db=None)
            intent = result.get("category", "unknown")
            print(f"[Planner] LLM classified intent as: {intent}")
        except Exception as e:
            print(f"[Planner WARN] LLM intent classification failed: {e}. Falling back to keywords.")
            intent = "unknown" # 키워드 기반으로 폴백
    
    # 2. 분류된 의도 또는 키워드 기반 라우팅
    
    # --- 고위험 작업 (High-Risk) ---
    if intent == "mail_send" or "메일 보내줘" in user_input or "메일 발송" in user_input:
         return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "send", "args": {"subject": user_input, "to": ["placeholder@example.com"], "body": "..."}}]
        }
    
    if intent == "ocr" or "화면" in user_input or "캡처" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "screen", "op": "ocr", "args": {"lang": "kor+eng"}}]
        }

    # --- 일반 작업 (Low-Risk) ---
    if intent == "schedule" or "일정" in user_input or "캘린더" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "create", "args": {"title": user_input}}]
        }
        
    if intent == "mail_compose" or "메일" in user_input: # '메일 보내줘'가 아닌 '메일'
        return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "compose", "args": {"subject": user_input}}]
        }

    if intent == "search" or "검색" in user_input or "찾아줘" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "browser", "op": "search", "args": {"query": user_input}}]
        }

    if intent == "notes" or "노트" in user_input or "메모" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "notes", "op": "save", "args": {"title": user_input, "body": user_input}}]
        }

    # 3. 기본값 (요약)
    return {
        "intent": user_input,
        "steps": [{"tool": "nlp", "op": "summarize", "args": {"text": user_input}}]
    }