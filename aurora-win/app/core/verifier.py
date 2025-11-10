from typing import Dict, Any


HIGH_RISK_TOOLS = {"system", "mail"}


def assess_risk(plan: Dict[str, Any], policy) -> str:
steps = plan.get("steps", [])
for s in steps:
t = s.get("tool")
if t in HIGH_RISK_TOOLS:
return "high"
return "low"


def need_consent(risk: str, plan: Dict[str, Any], policy) -> bool:
if risk == "high":
return True
return policy.require_each_time