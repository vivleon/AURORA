"""
Planner Consent Gate
- Hook for cognition pipeline: before executing a high-risk plan, emit a consent request payload
- Returns either {"proceed": True} or {"requires_consent": payload}

Usage:
    from planner_consent_gate.py import evaluate_consent
    decision = evaluate_consent(session_id, plan)
    if decision.get("requires_consent"):
        # return to UI; UI will call /consent/request then /consent/decision
    else:
        # proceed with executor
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

HIGH_RISK_ACTIONS = {"mail.send", "system.exec.limited", "files.delete", "payment.charge"}

@dataclass
class Plan:
    intent: str
    tool: str
    args: Dict[str, Any]
    risk: str  # low|medium|high


def evaluate_consent(session_id: str, plan: Plan) -> Dict[str, Any]:
    risk = plan.risk.lower()
    # heuristics: explicit high risk OR in known high-risk actions
    is_high = risk == "high" or plan.tool in HIGH_RISK_ACTIONS
    if not is_high:
        return {"proceed": True}

    purpose = plan.args.get("purpose") or f"Execute {plan.tool} for {plan.intent}"
    scope = plan.args.get("scope") or plan.tool.split(".")[0]
    ttl = int(plan.args.get("ttl_hours", 24))

    payload = {
        "session_id": session_id,
        "action": plan.tool,
        "purpose": purpose,
        "scope": scope,
        "risk": "high",
        "ttl_hours": ttl,
    }
    return {"requires_consent": payload}

# Example
if __name__ == "__main__":
    p = Plan(intent="send_summary", tool="mail.send", args={"to":"a@b.com"}, risk="high")
    print(evaluate_consent("sess-123", p))
