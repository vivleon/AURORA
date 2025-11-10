from typing import Dict, Any


def make_plan(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
# 간단한 규칙 베이스 + 키워드 라우팅 (후속으로 LLM 의도분석 연결)
if "일정" in user_input:
return {"steps": [{"tool": "calendar", "op": "create", "args": {"title": user_input}}]}
if "메일" in user_input:
return {"steps": [{"tool": "mail", "op": "compose", "args": {"subject": user_input}}]}
return {"steps": [{"tool": "nlp", "op": "summarize", "args": {"text": user_input}}]}