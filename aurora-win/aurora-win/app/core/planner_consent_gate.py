from dataclasses import dataclass
from typing import Dict, Any


RATIONALE_MAX = 240 # ~2 lines in UI


@dataclass
class Plan:
intent: str
tool: str
args: Dict[str, Any]
risk: str = "low"


HIGH_RISK = {"mail.send", "system.exec.limited", "files.delete", "payment.charge", "os.settings", "update.apply"}




def _summarize(text: str) -> str:
t = (text or "").strip().replace("\n", " ")
return (t[:RATIONALE_MAX] + "…") if len(t) > RATIONALE_MAX else t




def evaluate_consent(session_id: str, plan: Plan) -> Dict[str, Any]:
# basic gate: high-risk tool or explicit risk field
tool_key = plan.tool.strip()
is_high = plan.risk == "high" or tool_key in HIGH_RISK
if not is_high:
return {}


rationale = {
"why": _summarize(plan.intent or plan.args.get("purpose", "")),
"how": _summarize(f"tool={plan.tool} args={list(plan.args.keys())}")
}


return {
"requires_consent": {
"session_id": session_id,
"purpose": plan.args.get("purpose"),
"scope": plan.args.get("scope"),
"risk": plan.risk if plan.risk else "high",
"ttl_hours": plan.args.get("ttl_hours", 24),
"rationale": rationale
}
}