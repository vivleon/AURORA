# app/core/planner.py
from typing import Dict, Any
from app.router import model_runner
from app.tools import nlp

async def make_plan(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    [업그레이드 3.0]
    RAG 검색(rag_search) 의도를 추가합니다.
    """
    
    intent = "unknown"
    
    # 1. LLM 기반 의도 분류 시도
    if model_runner:
        try:
            # [수정] 'rag_search' (RAG 검색) 의도 추가
            categories = [
                "schedule_create", "schedule_find", 
                "mail_send", "mail_compose", 
                "search", "ocr", "summarize", "notes",
                "rag_search" # [신규]
            ]
            result = await nlp.classify({"text": user_input, "categories": categories}, policy=None, db=None)
            intent = result.get("category", "unknown")
            print(f"[Planner] LLM classified intent as: {intent}")
        except Exception as e:
            print(f"[Planner WARN] LLM intent classification failed: {e}. Falling back to keywords.")
            intent = "unknown"
    
    # 2. 분류된 의도 또는 키워드 기반 라우팅
    
    # [신규] RAG 검색 라우팅 (웹 검색보다 우선순위 높게)
    if intent == "rag_search" or "내 노트에서" in user_input or "기억에서" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "rag", "op": "search", "args": {"query": user_input}}]
        }

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
    
    if intent == "schedule_find" or "빈 시간" in user_input or "일정 추천" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "list_slots", "args": {"duration_min": 30}}]
        }

    if intent == "schedule_create" or "일정 잡아줘" in user_input or "캘린더" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "create", "args": {"title": user_input}}]
        }
        
    if intent == "mail_compose" or "메일" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "compose", "args": {"subject": user_input}}]
        }

    # [수정] RAG와 겹치지 않도록 키워드 명확화 (예: '웹 검색')
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