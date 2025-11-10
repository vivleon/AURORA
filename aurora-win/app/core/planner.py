from typing import Dict, Any

def make_plan(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자 입력을 받아 실행 계획(steps)을 생성합니다.
    [수정] 'op' (operation) 필드를 명시적으로 지정하여
    verifier.py와 executor.py가 올바르게 동작하도록 합니다.
    """
    
    # '일정' -> 'calendar.create'
    if "일정" in user_input or "캘린더" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "calendar", "op": "create", "args": {"title": user_input}}]
        }
        
    # '메일 보내줘' -> 'mail.send' (고위험 작업)
    if "메일 보내줘" in user_input or "메일 발송" in user_input:
         return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "send", "args": {"subject": user_input, "to": ["placeholder@example.com"], "body": "..."}}]
        }
        
    # '메일' -> 'mail.compose' (안전한 작업)
    if "메일" in user_input:
        return {
            "intent": user_input,
            "steps": [{"tool": "mail", "op": "compose", "args": {"subject": user_input}}]
        }
        
    # 기본값 -> 'nlp.summarize'
    return {
        "intent": user_input,
        "steps": [{"tool": "nlp", "op": "summarize", "args": {"text": user_input}}]
    }