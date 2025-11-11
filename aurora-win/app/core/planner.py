# app/core/planner.py
from typing import Dict, Any
from app.router import model_runner
from app.tools import nlp

async def make_plan(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    [업그레이드 4.0]
    LLM 의도 분류기를 사용하여 정확한 도구로 라우팅합니다.
    """
    
    intent = "unknown"
    
    # 1. LLM 기반 의도 분류 시도
    if model_runner:
        try:
            categories = [
                "schedule_create", "schedule_find", 
                "mail_send", "mail_compose", 
                "search", "ocr", "summarize", "notes",
                "rag_search"
            ]
            result = await nlp.classify({"text": user_input, "categories": categories}, policy=None, db=None)
            intent = result.get("category", "unknown")
            print(f"[Planner] LLM classified intent as: {intent}")
        except Exception as e:
            print(f"[Planner WARN] LLM intent classification failed: {e}. Falling back to keywords.")
            intent = "unknown"
    
    # 2. 분류된 의도 또는 키워드 기반 라우팅
    
    # [FIX] "내일 일정 알려줘"가 'schedule_create'로 라우팅되도록 키워드 순서 및 조건 수정
    
    # --- RAG / 일정 (가장 구체적인) ---
    if intent == "rag_search" or "내 노트에서" in user_input or "기억에서" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "rag", "op": "search", "args": {"query": user_input}}]
        }
    if intent == "schedule_find" or "빈 시간" in user_input or "일정 추천" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "list_slots", "args": {"duration_min": 30}}]
        }
    if intent == "schedule_create" or "일정 잡아줘" in user_input or "캘린더" in user_input or "내일 일정" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "create", "args": {"title": user_input}}]
        }

    # --- 고위험 작업 ---
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

    # --- 일반 작업 ---
    if intent == "mail_compose" or "메일" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "compose", "args": {"subject": user_input}}]
        }
    if intent == "search" or "웹 검색" in user_input or "찾아줘" in user_input:
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