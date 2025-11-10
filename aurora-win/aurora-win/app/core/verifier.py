from typing import Dict, Any

# planner_consent_gate.py와 동일한 고위험 작업(op) 목록을 사용
HIGH_RISK_OPS = {
    "mail.send", 
    "system.exec",
    "system.exec.limited", 
    "files.delete", 
    "payment.charge", 
    "os.settings", 
    "update.apply"
}


def assess_risk(plan: Dict[str, Any], policy) -> str:
    """
    계획(plan)에 포함된 개별 '작업(op)'이 고위험 목록에 있는지 확인합니다.
    """
    steps = plan.get("steps", [])
    for s in steps:
        # "mail.compose"가 아닌 "mail.send"처럼 (tool.op) 조합으로 검사
        op_key = f"{s.get('tool')}.{s.get('op')}"
        if op_key in HIGH_RISK_OPS:
            return "high"  # 고위험 작업이 하나라도 포함되면 즉시 'high' 반환
            
    return "low" # 고위험 작업이 없으면 'low'


def need_consent(risk: str, plan: Dict[str, Any], policy) -> bool:
    """
    위험도가 'high'이거나, 정책(policy.json)에서 'require_each_time'이 
    True로 설정된 경우 동의가 필요합니다.
    """
    if risk == "high":
        return True
    
    # policy.require_each_time은 app/main.py에서 로드된 
    # Policy 객체를 통해 접근합니다.
    return policy.require_each_time