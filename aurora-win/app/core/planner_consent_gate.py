from dataclasses import dataclass
from typing import Dict, Any


RATIONALE_MAX = 240 # ~2 lines in UI


@dataclass
class Plan:
    intent: str
    tool: str # 'tool.op' 형식 (예: "mail.send")
    args: Dict[str, Any]
    risk: str = "low"


# 'aurora-win/data/policy.json'의 'high_risk'와 일치해야 함
HIGH_RISK = {"mail.send", "system.exec.limited", "files.delete", "payment.charge", "os.settings", "update.apply", "system.exec"}


def _summarize(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    return (t[:RATIONALE_MAX] + "…") if len(t) > RATIONALE_MAX else t


def evaluate_consent(session_id: str, plan: Plan) -> Dict[str, Any]:
    """
    'plan.tool'은 'mail.send'와 같은 'tool.op' 형식이어야 합니다.
    """
    tool_key = plan.tool.strip()
    is_high = plan.risk == "high" or tool_key in HIGH_RISK
    
    if not is_high:
        # 동의가 필요 없으면 빈 객체 반환 (app/main.py의 로직과 일치)
        return {}

    # 동의가 필요함: UI에 전달할 페이로드 생성
    rationale = {
        "why": _summarize(plan.intent or plan.args.get("purpose", "")),
        "how": _summarize(f"tool={plan.tool} args={list(plan.args.keys())}")
    }

    return {
        "requires_consent": {
            "session_id": session_id,
            "action": plan.tool, # 'mail.send'
            "purpose": plan.args.get("purpose", plan.intent),
            "scope": plan.tool.split(".")[0], # 'mail'
            "risk": "high", # 'high'로 강제
            "ttl_hours": plan.args.get("ttl_hours", 24),
            "rationale": rationale
        }
    }