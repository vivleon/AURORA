"""
data/policy.json [cite: vivleon/aurora/AURORA-main/aurora-win/data/policy.json]에 고위험 규칙(high-risk rules)을 병합/보장합니다.
(app/core/verifier.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/core/verifier.py]와 planner_consent_gate.py [cite: vivleon/aurora/AURORA-main/aurora-win/app/core/planner_consent_gate.py]의 HIGH_RISK 목록과 일치해야 함)
Usage: python scripts/policy_merge.py --file data/policy.json
"""
import json, argparse, sys, os
from pathlib import Path

# verifier.py/planner_consent_gate.py와 일치하는 고위험군
WANTED = [
    "payment.*", 
    "os.settings", 
    "update.apply", 
    "mail.send", 
    "system.exec",
    "system.exec.limited", 
    "files.delete"
]

def main(path_str: str):
    path = Path(path_str)
    
    if not path.exists():
        print(f"[PolicyMerge] File not found, creating new: {path}")
        data = {"policy_version":"1.1","risk_rules":{}}
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to decode {path}. Creating new file.")
            data = {"policy_version":"1.1","risk_rules":{}}

    rr = data.setdefault("risk_rules", {})
    cur = set(rr.get("high_risk", []))
    cur.update(WANTED) # WANTED 목록을 강제로 추가
    
    rr["high_risk"] = sorted(list(cur))
    rr.setdefault("require_consent_each_time", True) # 기본값 보장
    data.setdefault("consent", {"require_each_time": True}) # 루트 consent 설정 보장

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[PolicyMerge] Updated {path} with high-risk rules.")
    except IOError as e:
        print(f"[ERROR] Failed to write policy file: {e}")

if __name__ == "__main__":
    default_path = Path(__file__).parent.parent / "data" / "policy.json"
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(default_path))
    args = ap.parse_args()
    main(args.file)